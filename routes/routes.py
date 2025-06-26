import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

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
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: list[str]
    start_date: str
    end_date: str

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_weather_data(latitude, longitude, parameters, start_date, end_date):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        return resp.json()

async def process_weather_fetch(entity: dict):
    """
    Workflow function applied before persisting 'weather_fetch' entity.
    Fetches weather data asynchronously, updates entity state with results or errors.
    """
    # Validate required input fields exist in entity
    try:
        latitude = entity["latitude"]
        longitude = entity["longitude"]
        parameters = entity["parameters"]
        start_date = entity["start_date"]
        end_date = entity["end_date"]
    except KeyError as e:
        entity["status"] = "failed"
        entity["error"] = f"Missing required field: {e.args[0]}"
        logger.error(entity["error"])
        return entity

    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"

    try:
        raw_weather = await fetch_weather_data(latitude, longitude, parameters, start_date, end_date)
        hourly_data = raw_weather.get("hourly", {})
        filtered_data = {param: hourly_data.get(param, []) for param in parameters}

        entity["status"] = "completed"
        entity["result"] = {
            "latitude": latitude,
            "longitude": longitude,
            "data": filtered_data,
            "date_range": {"start": start_date, "end": end_date},
        }
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
        entity.pop("error", None)
    except Exception as e:
        logger.exception("Error fetching weather data in workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
    return entity

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    try:
        initial_entity = {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "parameters": data.parameters,
            "start_date": data.start_date,
            "end_date": data.end_date,
        }

        id_returned = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch",
            entity_version=ENTITY_VERSION,
            entity=initial_entity
        )

        return jsonify(
            {
                "status": "success",
                "message": "Weather data fetch initiated",
                "request_id": str(id_returned),
            }
        )
    except Exception as e:
        logger.exception(f"Failed to initiate weather fetch: {e}")
        return jsonify({"status": "error", "message": "Failed to initiate weather fetch"}), 500

@app.route("/weather/result/<string:technical_id>", methods=["GET"])
async def weather_result(technical_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id,
        )
        if not job:
            return jsonify({"status": "error", "message": "Request ID not found"}), 404
        status = job.get("status")
        if status == "processing":
            return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
        if status == "failed":
            return jsonify({"status": "failed", "message": job.get("error", "Unknown error")} ), 500
        return jsonify(job.get("result", {}))
    except Exception as e:
        logger.exception(f"Error retrieving job result for {technical_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve data"}), 500

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
