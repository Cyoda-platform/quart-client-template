from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4
import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "databases" replaced by entity_service usage, so removed users_alerts, notifications_history, weather_processing_jobs

# Data classes for validation

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

# Notification sending mock
async def send_notification(user_id: str, alert_id: str, channel: str, target: str, message: str) -> bool:
    try:
        logger.info(f"Sending notification to user {user_id} via {channel} to {target}: {message}")
        if channel == "webhook":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(target, json={"alert_id": alert_id, "message": message})
                if resp.status_code >= 400:
                    logger.warning(f"Webhook notification failed: {resp.status_code} {resp.text}")
                    return False
        return True
    except Exception as e:
        logger.exception(e)
        return False

async def evaluate_alerts_for_weather_data(location: str, timestamp: str, temperature: float, rain_forecast: bool):
    alerts_triggered = []
    try:
        # Retrieve all alerts with status active
        condition = {"status": "active"}
        all_active_alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        # all_active_alerts is expected to be a list of alert entities, each having user_id etc.
        for alert in all_active_alerts:
            user_id = alert.get("user_id")
            if user_id is None:
                logger.warning(f"Alert missing user_id: {alert}")
                continue
            conditions = alert.get("conditions", [])
            matches = True
            for cond in conditions:
                ctype = cond.get("type")
                op = cond.get("operator")
                value = cond.get("value")
                if ctype == "temperature":
                    try:
                        val = float(value)
                        if op == "gt" and not (temperature > val):
                            matches = False
                        elif op == "lt" and not (temperature < val):
                            matches = False
                        elif op == "eq" and not (temperature == val):
                            matches = False
                    except Exception as e:
                        logger.warning(f"Invalid temperature condition in alert {alert.get('alert_id')}: {e}")
                        matches = False
                elif ctype == "rain_forecast":
                    val_bool = (str(value).lower() == "true")
                    if op == "eq" and rain_forecast != val_bool:
                        matches = False
                else:
                    logger.warning(f"Unknown condition type: {ctype}")
                    matches = False
                if not matches:
                    break
            if matches:
                notification_channels = alert.get("notification_channels", [])
                notification_targets = alert.get("notification_targets", {})
                alert_id = alert.get("alert_id")
                notification_results = []
                for channel in notification_channels:
                    target = None
                    if isinstance(notification_targets, dict):
                        target = notification_targets.get(channel)
                    elif isinstance(notification_targets, NotificationTargets):
                        target = getattr(notification_targets, channel, None)
                    if not target:
                        logger.warning(f"Missing notification target for channel {channel} in alert {alert_id}")
                        continue
                    message = f"Weather alert triggered for your rule '{alert.get('name')}' at {location}."
                    success = await send_notification(user_id, alert_id, channel, target, message)
                    notification_results.append({
                        "channel": channel,
                        "status": "sent" if success else "failed"
                    })
                    # Save notification history as an entity
                    notification_history_obj = {
                        "notification_id": str(uuid4()),
                        "alert_id": alert_id,
                        "channel": channel,
                        "status": "sent" if success else "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": user_id
                    }
                    try:
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="notifications_history",
                            entity_version=ENTITY_VERSION,
                            entity=notification_history_obj
                        )
                    except Exception as e:
                        logger.exception(f"Failed to save notification history: {e}")
                alerts_triggered.append({
                    "alert_id": alert_id,
                    "user_id": user_id,
                    "notification_channels": [r["channel"] for r in notification_results],
                    "notification_status": "sent" if all(r["status"] == "sent" for r in notification_results) else "failed"
                })
    except Exception as e:
        logger.exception(e)
    return alerts_triggered

async def process_weather_data(job_id: str, data: Dict[str, Any]):
    job_entity = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": datetime.now(timezone.utc).isoformat()
    }
    try:
        # Save job entity with status processing
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_processing_jobs",
            entity_version=ENTITY_VERSION,
            entity=job_entity
        )
    except Exception as e:
        logger.exception(f"Failed to save weather_processing_jobs job start: {e}")

    try:
        location = data.get("location")
        timestamp = data.get("timestamp")
        temperature = data.get("temperature")
        rain_forecast = data.get("rain_forecast")
        alerts_triggered = await evaluate_alerts_for_weather_data(location, timestamp, temperature, rain_forecast)
        # Update job status to completed
        job_entity_update = {
            "status": "completed",
            "alerts_triggered": alerts_triggered,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        # Assuming we can get technical_id by job_id for update - emulate by retrieving the job entity by condition
        jobs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="weather_processing_jobs",
            entity_version=ENTITY_VERSION,
            condition={"job_id": job_id}
        )
        if jobs:
            technical_id = jobs[0].get("technical_id")
            if technical_id:
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="weather_processing_jobs",
                    entity_version=ENTITY_VERSION,
                    entity=job_entity_update,
                    technical_id=technical_id,
                    meta={}
                )
    except Exception as e:
        logger.exception(e)
        # Update job status to failed
        try:
            jobs = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="weather_processing_jobs",
                entity_version=ENTITY_VERSION,
                condition={"job_id": job_id}
            )
            if jobs:
                technical_id = jobs[0].get("technical_id")
                if technical_id:
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="weather_processing_jobs",
                        entity_version=ENTITY_VERSION,
                        entity={"status": "failed", "error": str(e)},
                        technical_id=technical_id,
                        meta={}
                    )
        except Exception as ex:
            logger.exception(f"Failed to update weather_processing_jobs to failed: {ex}")

# POST routes with @validate_request last (workaround issue)
@app.route("/alerts", methods=["POST"])
@validate_request(CreateAlertRequest)
async def create_alert(data: CreateAlertRequest):
    try:
        alert_obj = {
            "user_id": data.user_id,
            "name": data.name,
            "conditions": [cond.__dict__ for cond in data.conditions],
            "notification_channels": data.notification_channels,
            "notification_targets": data.notification_targets.__dict__ if data.notification_targets else {},
            "status": "active",
            "alert_id": str(uuid4())
        }
        alert_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_obj
        )
        # alert_id returned is technical_id, but we keep alert_id in entity as unique field
        return jsonify({"alert_id": alert_obj["alert_id"], "status": "active"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create alert"}), 500

@app.route("/alerts/<alert_id>", methods=["POST"])
@validate_request(UpdateAlertRequest)
async def update_alert(data: UpdateAlertRequest, alert_id):
    try:
        # Retrieve alert by alert_id field using condition
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
        # Prepare updated fields
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
            return jsonify({"alert_id": alert_id, "status": "updated"}), 200  # nothing to update
        # Merge with existing alert_entity fields to avoid overwriting fields with empty
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

@app.route("/alerts/<alert_id>/delete", methods=["POST"])
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

@app.route("/users/<user_id>/alerts", methods=["GET"])
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

@app.route("/weather/data", methods=["POST"])
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
            entity=job_entity
        )
        asyncio.create_task(process_weather_data(job_id, data.__dict__))
        return jsonify({"job_id": job_id, "status": "queued", "requestedAt": requested_at}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process weather data"}), 500

@app.route("/users/<user_id>/notifications", methods=["GET"])
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

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)