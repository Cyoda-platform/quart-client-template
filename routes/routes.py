import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_weather_external(params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPEN_METEO_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error when calling Open-Meteo API: {e}")
            raise

async def process_prototype(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function applied to the 'prototype' entity asynchronously before persistence.
    It processes the queued weather data fetch job.
    """
    status = entity.get("status")
    if status != "queued":
        # No processing needed if not queued
        return entity

    # Change status to processing (direct modification, will be persisted)
    entity["status"] = "processing"
    entity["processingStartedAt"] = datetime.utcnow().isoformat()

    input_params = entity.get("input", {})
    latitude = input_params.get("latitude")
    longitude = input_params.get("longitude")
    start_date = input_params.get("start_date")
    end_date = input_params.get("end_date")
    parameters = input_params.get("parameters", [])
    hourly = ",".join(parameters) if parameters else ""

    # Validate essential parameters early to avoid unnecessary external calls
    if latitude is None or longitude is None or not start_date or not end_date:
        entity["status"] = "failed"
        entity["errorMessage"] = "Missing required input parameters"
        entity["failedAt"] = datetime.utcnow().isoformat()
        return entity

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": hourly,
        "timezone": "auto",
    }

    try:
        external_data = await fetch_weather_external(params)
        hourly_data = external_data.get("hourly", {})
        timestamps = hourly_data.get("time", [])
        filtered_params: Dict[str, Any] = {}
        for param in parameters:
            filtered_params[param] = hourly_data.get(param, [])

        result = {
            "data_id": entity.get("technical_id") or entity.get("id") or "unknown",
            "latitude": latitude,
            "longitude": longitude,
            "parameters": filtered_params,
            "timestamps": timestamps,
        }

        entity["result"] = result
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception(f"Failed to fetch weather data in workflow for entity {entity.get('technical_id')}")
        entity["status"] = "failed"
        entity["result"] = None
        entity["errorMessage"] = str(e)
        entity["failedAt"] = datetime.utcnow().isoformat()

    return entity


@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def fetch_weather(data: FetchRequest):
    data_dict = data.__dict__
    # Create entity with status queued, workflow function will process it
    data_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="prototype",
        entity_version=ENTITY_VERSION,
        entity={
            "status": "queued",
            "requestedAt": datetime.utcnow().isoformat(),
            "input": data_dict,
            "result": None,
        },
    )
    return jsonify({
        "status": "success",
        "message": "Weather data fetch initiated",
        "data_id": str(data_id),
    })


@app.route("/weather/result/<data_id>", methods=["GET"])
async def get_weather_result(data_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            technical_id=data_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Data ID not found"}), 404

    if not job:
        return jsonify({"status": "error", "message": "Data ID not found"}), 404

    status = job.get("status")
    if status in ("queued", "processing"):
        return jsonify({"status": "processing", "message": "Data is being fetched"}), 202
    if status == "failed":
        return jsonify({"status": "failed", "message": "Failed to fetch weather data", "error": job.get("errorMessage")}), 500
    return jsonify(job.get("result"))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
