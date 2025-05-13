from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Blueprint, request, jsonify
from quart_schema import validate_request

import httpx
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

ENTITY_VERSION = None
from common.config.config import ENTITY_VERSION

@dataclass
class FetchWeatherRequest:
    location: str
    parameters: list
    date: str = None

async def fetch_weather_from_msgeomet(location: str, parameters: list, date: str = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"https://api.meteo.lt/v1/places/{location}/forecasts/long-term"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            forecasts = data.get("forecastTimestamps", [])
            if not forecasts:
                return {}
            forecast = forecasts[0]
            extracted = {}
            if "temperature" in parameters and "airTemperature" in forecast:
                extracted["temperature"] = forecast["airTemperature"]
            if "humidity" in parameters and "relativeHumidity" in forecast:
                extracted["humidity"] = forecast["relativeHumidity"]
            if "wind_speed" in parameters and "windSpeed" in forecast:
                extracted["wind_speed"] = forecast["windSpeed"]
            return extracted
        except Exception as e:
            logger.exception(f"Error fetching weather from MSC GeoMet: {e}")
            return None

async def process_entity_job(entity):
    # Ensure requestedAt is set
    if "requestedAt" not in entity:
        entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"
    # Set initial status
    entity["status"] = "queued"
    # Ensure technical_id is set for identification
    technical_id = entity.get("technical_id")
    if not technical_id:
        technical_id = str(uuid.uuid4())
        entity["technical_id"] = technical_id
    # Extract required parameters for async task
    location = entity.get("location")
    parameters = entity.get("parameters")
    date = entity.get("date")
    # Validate mandatory fields before scheduling task
    if not location or not parameters:
        entity["status"] = "error"
        entity["error"] = "Missing required fields: location and parameters"
        return entity
    # Schedule async task outside workflow context
    asyncio.create_task(_async_process_entity_job(technical_id, location, parameters, date))
    return entity

async def _async_process_entity_job(job_id: str, location: str, parameters: list, date: str):
    try:
        # Update status to processing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={"status": "processing"},
            meta={}
        )
        data = await fetch_weather_from_msgeomet(location, parameters, date)
        if data is None:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity={"status": "error", "result": {}, "error": "Failed to fetch weather data"},
                meta={}
            )
            return
        result_data = {
            "status": "completed",
            "result": {
                "location": location,
                "parameters": data,
                "date": date if date else datetime.utcnow().strftime("%Y-%m-%d"),
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
            }
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity=result_data,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Exception in async processing task for job_id {job_id}: {e}")
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity={"status": "error", "result": {}, "error": "Internal error during processing"},
                meta={}
            )
        except Exception as update_exc:
            logger.exception(f"Failed to update entity_job with error status for job_id {job_id}: {update_exc}")

@routes_bp.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    entity = {
        "location": data.location,
        "parameters": data.parameters,
        "date": data.date,
    }
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=entity
    )
    return jsonify({
        "status": "success",
        "fetch_id": entity_id,
        "message": "Data fetching started"
    })

@routes_bp.route("/weather/result/<string:fetch_id>", methods=["GET"])
async def get_result(fetch_id: str):
    job = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        technical_id=fetch_id
    )
    if not job:
        return jsonify({"status": "error", "message": "fetch_id not found"}), 404
    status = job.get("status")
    if status in ("processing", "queued"):
        return jsonify({"status": "processing", "message": "Result not ready yet"}), 202
    if status == "error":
        return jsonify({"status": "error", "message": job.get("error", "Failed to fetch data")}), 500
    return jsonify({
        "fetch_id": fetch_id,
        **job.get("result", {}),
    })