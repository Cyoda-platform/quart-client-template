from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# Data classes for request validation
@dataclass
class Location:
    city: str = None
    latitude: float = None
    longitude: float = None

@dataclass
class WeatherFetchRequest:
    location: dict  # dynamic structure, so no nested dataclass here
    data_type: str

# TODO: Replace with your actual OpenWeatherMap API key
OPENWEATHER_API_KEY = "your_openweathermap_api_key"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def fetch_current_weather(location):
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have either city or latitude & longitude")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/weather", params=params)
        resp.raise_for_status()
        return resp.json()


async def fetch_forecast_weather(location):
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have either city or latitude & longitude")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/forecast", params=params)
        resp.raise_for_status()
        return resp.json()


async def process_weather_fetch(job_id, payload):
    try:
        location = payload.get("location", {})
        data_type = payload.get("data_type", "current")

        if data_type == "current":
            weather_data = await fetch_current_weather(location)
        elif data_type == "forecast":
            weather_data = await fetch_forecast_weather(location)
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

        record = {
            "weather_id": job_id,
            "location": location,
            "data_type": data_type,
            "weather_data": weather_data,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
        }

        # Update the entity_service with the final record
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=record,
            technical_id=job_id,
            meta={}
        )

        logger.info(f"Weather data stored for job_id={job_id}")

    except Exception as e:
        logger.exception(e)
        error_record = {
            "status": "failed",
            "error": str(e),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }

        # Update item with failure status
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=error_record,
            technical_id=job_id,
            meta={}
        )


@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)  # POST validation must go last for workaround
async def weather_fetch(data: WeatherFetchRequest):
    try:
        payload = data.__dict__

        job_id = str(uuid.uuid4())
        initial_record = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Add initial record to entity_service
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity={"weather_id": job_id, **initial_record}
        )

        asyncio.create_task(process_weather_fetch(job_id, payload))

        return jsonify(
            {
                "status": "success",
                "weather_id": job_id,
                "message": "Data fetch started successfully",
            }
        )

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/weather/<weather_id>", methods=["GET"])
async def weather_get(weather_id):
    try:
        record = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            technical_id=weather_id
        )
        if not record:
            return jsonify({"status": "error", "message": "weather_id not found"}), 404

        if record.get("status") == "processing":
            return jsonify(
                {
                    "weather_id": weather_id,
                    "status": "processing",
                    "message": "Data is still being fetched, please try again later",
                }
            ), 202

        if record.get("status") == "failed":
            return jsonify(
                {
                    "weather_id": weather_id,
                    "status": "failed",
                    "error": record.get("error", "Unknown error"),
                }
            ), 500

        response = {
            "weather_id": record["weather_id"],
            "location": record["location"],
            "data_type": record["data_type"],
            "weather_data": record["weather_data"],
            "fetched_at": record["fetched_at"],
        }
        return jsonify(response)

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)