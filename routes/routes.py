from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # TODO: Replace with your real API key
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass
class Location:
    type: str  # e.g. "city", "coordinates", "zipcode"
    value: str  # e.g. "London", "51.5074,-0.1278", "90210"


@dataclass
class FetchWeatherRequest:
    location: Location
    parameters: list = None  # Optional list of requested data fields


@routes_bp.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    # Compose initial entity_job data
    entity_data = {
        "location": {"type": data.location.type, "value": data.location.value},
        "parameters": data.parameters or [],
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        # technical_id is not set here; entity_service may generate it or workflow generates if missing
    }

    try:
        # Add entity_job with workflow function that will perform all async processing before persistence
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )
        # Return the entity_id assigned by entity_service
        return jsonify({"request_id": entity_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to register job"}), 500


@routes_bp.route("/weather/results/<string:request_id>", methods=["GET"])
async def get_weather_results(request_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Request ID not found"}), 404

    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    status = job.get("status")
    if status in ("processing", "pending"):
        return jsonify({"request_id": request_id, "status": "processing"}), 202

    if status == "failed":
        return jsonify({"request_id": request_id, "status": "failed", "message": job.get("message")}), 500

    try:
        result = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_results",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Results not found"}), 404

    if not result:
        return jsonify({"error": "Results not found"}), 404

    return jsonify(result)