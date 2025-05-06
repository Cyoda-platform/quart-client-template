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
class AlertCondition:
    condition_type: str
    operator: str
    threshold: float or bool

@dataclass
class NotificationDetails:
    email: str = None
    sms: str = None
    webhook_url: str = None

@dataclass
class AlertRequest:
    alert_id: str = None
    user_id: str = None
    location: dict = None
    conditions: list = None
    notification_channels: list = None
    notification_details: NotificationDetails = None
    message_template: str = None

@dataclass
class WeatherFetchRequest:
    location: dict
    data_type: str

OPENWEATHER_API_KEY = "your_openweathermap_api_key"  # Replace with your actual API key
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

@routes_bp.route("/alerts", methods=["POST"])
@validate_request(AlertRequest)
async def create_or_update_alert(data: AlertRequest):
    try:
        alert = data.__dict__
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert,
        )
        return jsonify({"status": "success", "alert_id": alert.get("alert_id"), "message": "Alert created/updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@routes_bp.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    try:
        entity = {
            "location": data.location,
            "data_type": data.data_type,
            "weather_id": str(uuid.uuid4()),
            "status": "queued",
            "requestedAt": datetime.utcnow().isoformat() + "Z"
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity,
        )
        return jsonify({"status": "success", "weather_id": entity["weather_id"], "message": "Weather data fetch initiated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@routes_bp.route("/weather/<weather_id>", methods=["GET"])
async def get_weather(weather_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            technical_id=weather_id
        )
        if not entity:
            return jsonify({"status": "error", "message": "weather_id not found"}), 404

        status = entity.get("status")
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
                "error": entity.get("error", "Unknown error"),
            }), 500

        return jsonify(entity)
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@routes_bp.route("/alerts/<user_id>", methods=["GET"])
async def get_user_alerts(user_id):
    try:
        condition = {"user_id": user_id}
        user_alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify(user_alerts)
    except Exception as e:
        logger.exception(e)
        return jsonify([])