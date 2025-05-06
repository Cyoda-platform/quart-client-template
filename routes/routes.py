from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

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

@dataclass
class WeatherFetchRequest:
    location: dict
    data_type: str

@routes_bp.route("/weather/fetch", methods=["POST"])
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
            )

        return jsonify({
            "status": "success",
            "weather_id": weather_id,
            "message": "Weather data fetch initiated",
        })

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@routes_bp.route("/weather/<weather_id>", methods=["GET"])
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