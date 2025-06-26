from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx
from quart import Quart, request, jsonify
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

@app.route("/weather/fetch", methods=["POST"])
# workaround: validation must come last on POST due to quart_schema defect
@validate_request(WeatherFetchRequest)
async def fetch_weather(data: WeatherFetchRequest):
    latitude = data.latitude
    longitude = data.longitude
    parameters = data.parameters

    entity_name = "weather_fetch_request"
    entity_data = {
        "latitude": latitude,
        "longitude": longitude,
        "parameters": parameters,
        "requestedAt": datetime.utcnow().isoformat() + "Z"
    }

    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to start weather data fetching"}), 500

    # fire and forget process_entity task is no longer needed here because data fetching should be done externally now
    # just return the id
    return jsonify({
        "status": "success",
        "message": "Weather data fetching started",
        "dataId": str(id)  # ensure string id
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
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to retrieve data"}), 500

    if not entry:
        return jsonify({"status": "error", "message": "dataId not found"}), 404

    status = entry.get("status")
    if status == "processing":
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
    if status == "failed":
        return jsonify({"status": "error", "message": entry.get("error", "Unknown error")}), 500

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