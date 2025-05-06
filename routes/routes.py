from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from quart import Blueprint, request, jsonify
from quart_schema import validate_request
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class Condition:
    type: str
    operator: str
    value: Any

@dataclass
class NotificationTargets:
    email: Optional[str] = None
    sms: Optional[str] = None
    webhook: Optional[str] = None

@dataclass
class CreateAlertRequest:
    user_id: str
    name: str
    conditions: List[Condition]
    notification_channels: List[str]
    notification_targets: NotificationTargets

@dataclass
class UpdateAlertRequest:
    name: Optional[str] = None
    conditions: Optional[List[Condition]] = None
    notification_channels: Optional[List[str]] = None
    notification_targets: Optional[NotificationTargets] = None

@dataclass
class WeatherDataRequest:
    location: str
    timestamp: str
    temperature: float
    rain_forecast: bool
    additional_data: Optional[Dict[str, Any]] = None

@routes_bp.route("/alerts", methods=["POST"])
@validate_request(CreateAlertRequest)
async def create_alert(data: CreateAlertRequest):
    try:
        alert_obj = {
            "user_id": data.user_id,
            "name": data.name,
            "conditions": [cond.__dict__ for cond in data.conditions],
            "notification_channels": data.notification_channels,
            "notification_targets": data.notification_targets.__dict__ if data.notification_targets else {},
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_obj,
        )
        return jsonify({"alert_id": alert_obj.get("alert_id"), "status": "active"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create alert"}), 500

@routes_bp.route("/alerts/<alert_id>", methods=["POST"])
@validate_request(UpdateAlertRequest)
async def update_alert(data: UpdateAlertRequest, alert_id):
    try:
        alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition={"alert_id": alert_id}
        )
        if not alerts:
            return jsonify({"error": "Alert not found"}), 404
        alert_entity = alerts[0]
        technical_id = alert_entity.get("technical_id")
        if technical_id is None:
            return jsonify({"error": "Alert technical ID missing"}), 500
        updated = {}
        if data.name is not None:
            updated["name"] = data.name
        if data.conditions is not None:
            updated["conditions"] = [cond.__dict__ for cond in data.conditions]
        if data.notification_channels is not None:
            updated["notification_channels"] = data.notification_channels
        if data.notification_targets is not None:
            updated["notification_targets"] = data.notification_targets.__dict__
        if not updated:
            return jsonify({"alert_id": alert_id, "status": "updated"}), 200
        alert_entity.update(updated)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_entity,
            technical_id=technical_id,
            meta={}
        )
        return jsonify({"alert_id": alert_id, "status": "updated"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update alert"}), 500

@routes_bp.route("/alerts/<alert_id>/delete", methods=["POST"])
async def delete_alert(alert_id):
    try:
        alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition={"alert_id": alert_id}
        )
        if not alerts:
            return jsonify({"error": "Alert not found"}), 404
        alert_entity = alerts[0]
        technical_id = alert_entity.get("technical_id")
        if technical_id is None:
            return jsonify({"error": "Alert technical ID missing"}), 500
        alert_entity["status"] = "deleted"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_entity,
            technical_id=technical_id,
            meta={}
        )
        return jsonify({"alert_id": alert_id, "status": "deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete alert"}), 500

@routes_bp.route("/users/<user_id>/alerts", methods=["GET"])
async def get_user_alerts(user_id):
    try:
        alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition={"user_id": user_id}
        )
        return jsonify(alerts), 200
    except Exception as e:
        logger.exception(e)
        return jsonify([]), 200

@routes_bp.route("/weather/data", methods=["POST"])
@validate_request(WeatherDataRequest)
async def post_weather_data(data: WeatherDataRequest):
    try:
        job_id = str(uuid4())
        requested_at = datetime.now(timezone.utc).isoformat()
        job_entity = {
            "job_id": job_id,
            "status": "queued",
            "requestedAt": requested_at,
            "location": data.location,
            "timestamp": data.timestamp,
            "temperature": data.temperature,
            "rain_forecast": data.rain_forecast,
            "additional_data": data.additional_data or {}
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_processing_jobs",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
        )
        return jsonify({"job_id": job_id, "status": "queued", "requestedAt": requested_at}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process weather data"}), 500

@routes_bp.route("/users/<user_id>/notifications", methods=["GET"])
async def get_notifications(user_id):
    try:
        notifications = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="notifications_history",
            entity_version=ENTITY_VERSION,
            condition={"user_id": user_id}
        )
        return jsonify(notifications), 200
    except Exception as e:
        logger.exception(e)
        return jsonify([]), 200