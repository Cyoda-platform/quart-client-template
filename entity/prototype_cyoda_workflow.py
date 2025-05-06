from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
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

@dataclass
class WeatherFetchRequest:
    location: dict
    data_type: str

OPENWEATHER_API_KEY = "your_openweathermap_api_key"  # Replace with your actual key
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

    async with httpx.AsyncClient(timeout=10.0) as client:
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

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/forecast", params=params)
        resp.raise_for_status()
        return resp.json()

async def process_weather(entity):
    """
    Workflow function applied before persisting the weather entity.
    Executes the async fetch of weather data and updates entity state.
    """
    try:
        # Ensure entity has weather_id and created_at
        entity['weather_id'] = entity.get('weather_id') or str(uuid.uuid4())
        entity['created_at'] = entity.get('created_at') or datetime.utcnow().isoformat() + "Z"

        # Mark as processing on workflow start
        entity['status'] = 'processing'

        location = entity.get("location", {})
        data_type = entity.get("data_type", "current")

        # Fetch weather data according to the data_type
        if data_type == "current":
            weather_data = await fetch_current_weather(location)
        elif data_type == "forecast":
            weather_data = await fetch_forecast_weather(location)
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

        # Update entity with fetched data
        entity['weather_data'] = weather_data
        entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"
        entity['status'] = 'completed'

    except Exception as e:
        logger.exception(f"Error in workflow process_weather for id={entity.get('weather_id')}: {e}")
        entity['status'] = 'failed'
        entity['error'] = str(e)
        entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"

    return entity

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    try:
        payload = data.__dict__
        weather_id = str(uuid.uuid4())

        entity = {
            'weather_id': weather_id,
            'location': payload.get('location'),
            'data_type': payload.get('data_type'),
            'status': 'queued',
            'requestedAt': datetime.utcnow().isoformat() + "Z",
        }

        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_weather
        )

        return jsonify({
            "status": "success",
            "weather_id": weather_id,
            "message": "Weather data fetch initiated",
        })

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

        status = record.get("status")
        if status in ("processing", "queued"):
            return jsonify({
                "weather_id": weather_id,
                "status": status,
                "message": "Data is being fetched, please try again later",
            }), 202

        if status == "failed":
            return jsonify({
                "weather_id": weather_id,
                "status": "failed",
                "error": record.get("error", "Unknown error"),
            }), 500

        # status == completed
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