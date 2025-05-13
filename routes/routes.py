import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

import httpx
from quart import Blueprint, request, jsonify
from quart_schema import validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class WeatherFetchRequest:
    location: str
    parameters: List[str]
    datetime: Optional[str]

@dataclass
class WeatherResultsQuery:
    location: str

async def fetch_weather_from_external_api(location: str, parameters: List[str], datetime_iso: Optional[str]) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            params = {"key": "demo", "q": location, "aqi": "no"}
            response = await client.get("http://api.weatherapi.com/v1/current.json", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            current = data.get("current", {})
            result = {}
            if "temperature" in parameters:
                result["temperature"] = current.get("temp_c")
            if "humidity" in parameters:
                result["humidity"] = current.get("humidity")
            if "wind_speed" in parameters:
                result["wind_speed"] = current.get("wind_kph")
            for param in parameters:
                if param not in result:
                    result[param] = None
            return result
        except Exception:
            logger.exception(f"Failed to fetch weather for location={location}")
            return {}

async def process_weather_fetch_result(entity: dict) -> dict:
    # Currently no modification needed, placeholder for future enhancements
    return entity

async def process_weather_fetch_request(entity: dict) -> dict:
    entity['timestamp'] = datetime.utcnow().isoformat()

    location = entity.get("location")
    parameters = entity.get("parameters")
    datetime_iso = entity.get("datetime")

    if not location or not isinstance(parameters, list) or len(parameters) == 0:
        logger.warning(f"Invalid weather fetch request entity data: {entity}")
        # Persist entity as-is; do not spawn fetch task
        return entity

    # In case entity id is not set yet, we set a temporary placeholder and update later if possible
    request_id = entity.get("id")
    if not request_id:
        # id likely assigned after persistence; we cannot wait here
        request_id = ""

    async def fetch_and_store():
        try:
            weather_data = await fetch_weather_from_external_api(location, parameters, datetime_iso)
            result_entity = {
                "request_id": str(request_id),
                "location": location,
                "timestamp": datetime.utcnow().isoformat(),
                "data": weather_data
            }
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="weather_fetch_result",
                entity_version=ENTITY_VERSION,
                entity=result_entity
            )
            logger.info(f"Stored weather_fetch_result for location={location}, request_id={request_id}")
        except Exception:
            logger.exception("Error in fetch_and_store workflow function")

    # Schedule background task; do not await to avoid delaying persistence
    asyncio.create_task(fetch_and_store())

    return entity

@routes_bp.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    try:
        added_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__
        )
        return jsonify({
            "status": "success",
            "message": "Weather fetch request accepted. Processing started.",
            "data": {"id": str(added_id)}
        })
    except Exception:
        logger.exception("Failed to process weather fetch request")
        return jsonify({"status": "failure", "message": "Failed to start weather fetch"}), 500

@routes_bp.route("/weather/results", methods=["GET"])
@validate_querystring(WeatherResultsQuery)
async def weather_results():
    location = request.args.get("location")
    if not location:
        return jsonify({"message": "Missing required query parameter: location"}), 400
    entity_name = "weather_fetch_result"
    try:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.location",
                        "operatorType": "EQUALS",
                        "value": location,
                        "type": "simple"
                    }
                ]
            }
        }
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not items:
            return jsonify({"message": "No data available for the requested location"}), 404

        latest = max(items, key=lambda x: x.get("timestamp", ""))
        return jsonify({
            "location": location,
            "timestamp": latest.get("timestamp"),
            "data": latest.get("data")
        })
    except Exception:
        logger.exception("Error retrieving weather results")
        return jsonify({"message": "Error retrieving weather results"}), 500