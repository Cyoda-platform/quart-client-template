import asyncio
import logging
from datetime import datetime
from typing import List
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

# workaround: quart-schema defect requires validate_request after route decorator for POST
@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    # Basic sanity checks (could be improved)
    required_fields = {"latitude", "longitude", "parameters", "start_date", "end_date"}
    if not data or not required_fields.issubset(data.__dict__.keys()):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__
        )
        return jsonify({"request_id": id}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add item"}), 500

@app.route("/weather/result/<string:request_id>", methods=["GET"])
async def weather_result(request_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
        if not job:
            return jsonify({"error": "Request ID not found"}), 404

        status = job.get("status", "processing")
        if status == "processing":
            return jsonify({"request_id": request_id, "status": "processing"}), 200
        elif status == "completed":
            return jsonify({
                "request_id": request_id,
                "status": "completed",
                "data": job.get("data", {})
            }), 200
        elif status == "failed":
            return jsonify({
                "request_id": request_id,
                "status": "failed",
                "error": job.get("error", "Unknown error")
            }), 500
        else:
            return jsonify({"error": "Unknown job status"}), 500
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve item"}), 500

async def fetch_weather_data(latitude: float, longitude: float, parameters: List[str], start_date: str, end_date: str):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch weather data: {e}")
            raise

async def process_entity(job_id: str, data: dict):
    try:
        raw_data = await fetch_weather_data(
            latitude=data["latitude"],
            longitude=data["longitude"],
            parameters=data["parameters"],
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        hourly = raw_data.get("hourly", {})
        processed = {"dates": hourly.get("time", [])}
        for param in data["parameters"]:
            processed[param] = hourly.get(param, [])

        # Update entity_service with processed results and status
        update_data = {
            "status": "completed",
            "data": processed,
            "completedAt": datetime.utcnow().isoformat()
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        error_data = {
            "status": "failed",
            "error": str(e)
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=error_data,
            technical_id=job_id,
            meta={}
        )
        logger.exception(f"Job {job_id} failed.")

@app.before_serving
async def start_background_tasks():
    # This will keep track of running background tasks in memory
    # We no longer use local cache for jobs storage, so we need to fetch jobs with "processing" status and resume tasks if needed
    try:
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            condition={
                "cyoda": {
                    "type": "group",
                    "operator": "AND",
                    "conditions": [
                        {
                            "jsonPath": "$.status",
                            "operatorType": "EQUALS",
                            "value": "processing",
                            "type": "simple"
                        }
                    ]
                }
            }
        )
        for item in items:
            technical_id = item.get("technical_id") or item.get("id")
            data = item.get("entity") or item
            if technical_id and data:
                asyncio.create_task(process_entity(str(technical_id), data))
    except Exception as e:
        logger.exception(f"Failed to resume processing tasks on startup: {e}")

@app.route("/weather/process/<string:request_id>", methods=["POST"])
async def trigger_processing(request_id):
    # Endpoint to manually trigger processing if needed
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
        if not item:
            return jsonify({"error": "Request ID not found"}), 404
        data = item.get("entity") or item
        asyncio.create_task(process_entity(request_id, data))
        return jsonify({"request_id": request_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to trigger processing"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)