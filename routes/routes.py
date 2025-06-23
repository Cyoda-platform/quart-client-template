from dataclasses import dataclass
from typing import List
import logging
from datetime import datetime

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

routes_bp = Blueprint('routes', __name__)

@dataclass
class WeatherFetch:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

async def fetch_weather_data(latitude, longitude, parameters, start_date, end_date):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "UTC",
        "hourly": ",".join(parameters),
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        return response.json()

async def process_weather_fetch_job(entity: dict):
    """
    Workflow function for 'weather_fetch_job' entity.
    Runs asynchronously before the entity is persisted.
    Modifies entity in-place to set status and results.
    """
    entity.setdefault("created_at", datetime.utcnow().isoformat() + "Z")
    entity["status"] = "processing"
    try:
        entity["status"] = "fetching"
        weather_data = await fetch_weather_data(
            entity["latitude"],
            entity["longitude"],
            entity["parameters"],
            entity["start_date"],
            entity["end_date"],
        )
        result_data = {
            "latitude": entity["latitude"],
            "longitude": entity["longitude"],
            "parameters": weather_data.get("hourly", {}),
            "start_date": entity["start_date"],
            "end_date": entity["end_date"],
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
        entity["result"] = result_data
        entity["status"] = "completed"
        # Clear error if previously set
        entity.pop("error", None)
    except Exception as e:
        logger.exception("Weather fetch failed in workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        # Clear result if previously set
        entity.pop("result", None)
    return entity

@routes_bp.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetch)
async def weather_fetch(data: WeatherFetch):
    # Prepare entity data dict
    data_dict = data.__dict__.copy()
    # Workflow sets status and timestamps
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
    except Exception as e:
        logger.exception("Failed to add weather_fetch_job entity")
        return jsonify({"status": "error", "message": "Failed to initiate weather fetch"}), 500

    return jsonify({
        "status": "success",
        "message": "Weather data fetch completed or failed, see status",
        "request_id": job_id,
    })

@routes_bp.route("/weather/result/<string:job_id>", methods=["GET"])
async def weather_result(job_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Request ID not found"}), 404

    if not job:
        return jsonify({"status": "error", "message": "Request ID not found"}), 404

    status = job.get("status")
    if status in ("processing", "fetching"):
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
    if status == "failed":
        return jsonify({"status": "failed", "error": job.get("error", "Unknown error")}), 500
    return jsonify({"status": "success", "data": job.get("result")})