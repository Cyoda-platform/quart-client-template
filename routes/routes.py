from common.grpc_client.grpc_client import grpc_stream
from dataclasses import dataclass
from typing import Optional

import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class Location:
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@dataclass
class FetchWeatherRequest:
    location: Location
    data_type: str  # "current", "forecast", or "historical"

@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    location = data.location
    if not (location.city or (location.latitude is not None and location.longitude is not None)):
        return jsonify({"message": "Location must include 'city' or both 'latitude' and 'longitude'"}), 400

    request_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    entity_data = {
        "request_id": request_id,
        "status": "processing",
        "requestedAt": requested_at,
        "location": {
            "city": location.city,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "data_type": data.data_type,
        "weather_data": None,
        "error_message": None,
    }

    add_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=entity_data,
        )

    return jsonify({"request_id": add_id, "status": "processing", "message": "Request accepted"}), 202

@app.route("/weather/result/<request_id>", methods=["GET"])
async def get_weather_result(request_id):
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        technical_id=request_id,
    )
    if not job:
        return jsonify({"message": "Request ID not found"}), 404

    response = {
        "request_id": job.get("request_id", request_id),
        "location": job.get("location"),
        "data_type": job.get("data_type"),
        "status": job.get("status"),
    }

    if job.get("status") == "completed":
        response["weather_data"] = job.get("weather_data")
    elif job.get("status") == "failed":
        response["error_message"] = job.get("error_message")

    return jsonify(response)

if __name__ == '__main__':
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s'
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)