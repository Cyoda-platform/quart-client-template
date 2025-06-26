 from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

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

async def process_weather_fetch_request(entity: Dict[str, Any]) -> None:
    """
    Workflow function applied to the weather_fetch_request entity before persistence.
    This asynchronously fetches weather data and modifies the entity state accordingly.
    """

    entity["status"] = "processing"
    entity["requestedAt"] = entity.get("requestedAt") or datetime.utcnow().isoformat() + "Z"

    latitude = entity.get("latitude")
    longitude = entity.get("longitude")
    parameters = entity.get("parameters", [])

    # Validate coordinates and parameters early to prevent unnecessary requests
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        entity["status"] = "failed"
        entity["error"] = "Invalid latitude or longitude"
        logger.error("Invalid latitude or longitude in entity")
        return

    if not parameters or not all(isinstance(p, str) for p in parameters):
        entity["status"] = "failed"
        entity["error"] = "Parameters must be a non-empty list of strings"
        logger.error("Invalid parameters in entity")
        return

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(parameters),
        "timezone": "UTC",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        entity["data"] = data
        entity["timestamp"] = datetime.utcnow().isoformat() + "Z"
        entity["status"] = "completed"
        if "error" in entity:
            del entity["error"]
        logger.info(f"Weather data fetched successfully for entity at {entity['timestamp']}")

    except httpx.RequestError as e:
        error_message = f"Network error while fetching weather data: {str(e)}"
        entity["status"] = "failed"
        entity["error"] = error_message
        logger.error(error_message)

    except httpx.HTTPStatusError as e:
        error_message = f"HTTP error while fetching weather data: {str(e)}"
        entity["status"] = "failed"
        entity["error"] = error_message
        logger.error(error_message)

    except Exception as e:
        error_message = f"Unexpected error while fetching weather data: {str(e)}"
        entity["status"] = "failed"
        entity["error"] = error_message
        logger.error(error_message)

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def fetch_weather(data: WeatherFetchRequest):
    entity_name = "weather_fetch_request"
    entity_data = {
        "latitude": data.latitude,
        "longitude": data.longitude,
        "parameters": data.parameters,
    }

    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
    except Exception as e:
        logger.exception("Failed to add weather_fetch_request entity")
        return jsonify({"status": "error", "message": "Failed to start weather data fetching"}), 500

    return jsonify({
        "status": "success",
        "message": "Weather data fetching started",
        "dataId": str(id)
    })

@app.route("/weather/result/<string:data_id>", methods=["GET"])
async def get_weather_result(data_id):
    entity_name = "weather_fetch_request"
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=data_id
        )
    except Exception as e:
        logger.exception("Failed to retrieve weather data")
        return jsonify({"status": "error", "message": "Failed to retrieve data"}), 500

    if not entry:
        return jsonify({"status": "error", "message": "dataId not found"}), 404

    status = entry.get("status")
    if status == "processing":
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
    if status == "failed":
        return jsonify({"status": "error", "message": entry.get("error", "Unknown error")}), 500
    if status != "completed":
        return jsonify({"status": "error", "message": f"Unexpected status: {status}"}), 500

    response = {
        "dataId": data_id,
        "latitude": entry.get("latitude"),
        "longitude": entry.get("longitude"),
        "parameters": {},
        "timestamp": entry.get("timestamp"),
    }

    data = entry.get("data", {})
    hourly = data.get("hourly", {})
    for param in entry.get("parameters", []):
        values = hourly.get(param)
        response["parameters"][param] = values[-1] if isinstance(values, list) else values

    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)