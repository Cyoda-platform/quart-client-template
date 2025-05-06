from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

entity_service = BeanFactory.get_bean("entity_service")
cyoda_auth_service = BeanFactory.get_bean("cyoda_auth_service")

OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # TODO: Replace with your real API key
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_weather_from_api(location_type: str, location_value: str, parameters: list):
    params = {"appid": OPENWEATHERMAP_API_KEY, "units": "metric"}

    if location_type == "city":
        params["q"] = location_value
    elif location_type == "coordinates":
        try:
            lat, lon = map(str.strip, location_value.split(","))
            params["lat"] = lat
            params["lon"] = lon
        except Exception:
            raise ValueError("Invalid coordinates format, expected 'lat,lon'")
    else:
        raise ValueError(f"Unsupported location type: {location_type}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(OPENWEATHERMAP_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    result = {}
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = data.get("weather", [{}])[0]

    if not parameters:
        parameters = ["temperature", "humidity", "wind_speed", "forecast"]

    if "temperature" in parameters:
        result["temperature"] = main.get("temp")
    if "humidity" in parameters:
        result["humidity"] = main.get("humidity")
    if "wind_speed" in parameters:
        result["wind_speed"] = wind.get("speed")
    if "forecast" in parameters:
        result["forecast"] = weather.get("description")

    return result


async def process_set_initial_state(entity: dict):
    entity["status"] = "processing"
    entity["requestedAt"] = entity.get("requestedAt") or datetime.utcnow().isoformat() + "Z"
    entity["message"] = ""
    entity["persistedAt"] = datetime.utcnow().isoformat() + "Z"


async def process_fetch_weather_data(entity: dict):
    location = entity.get("location")
    parameters = entity.get("parameters", [])

    if not location or "type" not in location or "value" not in location:
        raise ValueError("Invalid location data")

    location_type = location["type"]
    location_value = location["value"]

    weather_data = await fetch_weather_from_api(location_type, location_value, parameters)
    entity["weather_data"] = weather_data


async def process_add_results_entity(entity: dict):
    request_id = entity.get("technical_id")
    if not request_id:
        request_id = str(uuid.uuid4())
        entity["technical_id"] = request_id

    result_entity = {
        "technical_id": request_id,
        "request_id": request_id,
        "location": entity.get("location"),
        "data": entity.get("weather_data"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entity_version": ENTITY_VERSION
    }

    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_results",
        entity_version=ENTITY_VERSION,
        entity=result_entity,
        workflow=None
    )


async def process_set_success_state(entity: dict):
    entity["status"] = "completed"
    entity["message"] = "Weather data fetched successfully"
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"


async def process_set_failure_state(entity: dict, exc: Exception):
    entity["status"] = "failed"
    entity["message"] = str(exc)
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
    logger.exception("Error in process_entity_job workflow")