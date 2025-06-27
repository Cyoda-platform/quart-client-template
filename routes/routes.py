import asyncio
import logging
from datetime import datetime
from typing import List
from dataclasses import dataclass
import uuid

import httpx
from quart import Quart, jsonify
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
        response = await client.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

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
            "error": str(e),
        }
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="weather_fetch_request",
                entity_version=ENTITY_VERSION,
                entity=error_data,
                technical_id=job_id,
                meta={}
            )
        except Exception:
            # If update fails, log and continue to avoid crashing
            logger.exception(f"Failed to update failed status for job {job_id}")
        logger.exception(f"Job {job_id} failed.")

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__
        )
        return jsonify({"request_id": entity_id}), 202
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

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
