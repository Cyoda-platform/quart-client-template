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

async def process_alert(entity: Dict[str, Any]) -> None:
    if "status" not in entity:
        entity["status"] = "active"
    if "alert_id" not in entity:
        entity["alert_id"] = str(uuid4())
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()

async def process_notifications_history(entity: Dict[str, Any]) -> None:
    user_id = entity.get("user_id")
    alert_id = entity.get("alert_id")
    channel = entity.get("channel")
    if not all([user_id, alert_id, channel]):
        logger.warning("Missing fields for notifications_history entity, skipping send")
        return
    target = entity.get("target")
    if not target:
        logger.warning("No target found in notifications_history entity, skipping send")
        return
    message = entity.get("message", f"Alert {alert_id} triggered")
    try:
        logger.info(f"Sending notification via {channel} to {target} for user {user_id}")
        if channel == "webhook":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(target, json={"alert_id": alert_id, "message": message})
                if resp.status_code >= 400:
                    logger.warning(f"Webhook notification failed: {resp.status_code} {resp.text}")
                    entity["status"] = "failed"
                else:
                    entity["status"] = "sent"
        else:
            entity["status"] = "sent"
    except Exception as e:
        logger.exception(f"Failed to send notification: {e}")
        entity["status"] = "failed"

async def process_weather_processing_jobs(entity: Dict[str, Any]) -> None:
    if "status" not in entity or entity["status"] == "queued":
        entity["status"] = "processing"

    async def background_job(job_entity: Dict[str, Any]):
        job_id = job_entity.get("job_id")
        if not job_id:
            logger.error("Job entity missing job_id. Cannot process.")
            return
        location = job_entity.get("location")
        timestamp = job_entity.get("timestamp")
        temperature = job_entity.get("temperature")
        rain_forecast = job_entity.get("rain_forecast")

        try:
            alerts_triggered = []
            active_alerts = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="alert",
                entity_version=ENTITY_VERSION,
                condition={"status": "active"}
            )
            for alert in active_alerts:
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

                if not matches:
                    continue

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

                    notification_entity = {
                        "notification_id": str(uuid4()),
                        "alert_id": alert_id,
                        "channel": channel,
                        "status": "pending",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": user_id,
                        "target": target,
                        "message": message
                    }
                    try:
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="notifications_history",
                            entity_version=ENTITY_VERSION,
                            entity=notification_entity,
                            workflow=process_notifications_history
                        )
                        notification_results.append({"channel": channel, "status": "sent"})
                    except Exception as e:
                        logger.exception(f"Failed to add notifications_history entity: {e}")
                        notification_results.append({"channel": channel, "status": "failed"})

                alerts_triggered.append({
                    "alert_id": alert_id,
                    "user_id": user_id,
                    "notification_channels": [r["channel"] for r in notification_results],
                    "notification_status": "sent" if all(r["status"] == "sent" for r in notification_results) else "failed"
                })

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
                        entity={
                            "status": "completed",
                            "alerts_triggered": alerts_triggered,
                            "processed_at": datetime.now(timezone.utc).isoformat()
                        },
                        technical_id=technical_id,
                        meta={}
                    )
        except Exception as exc:
            logger.exception(f"Exception in background job processing weather data: {exc}")
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
                            entity={
                                "status": "failed",
                                "error": str(exc),
                                "processed_at": datetime.now(timezone.utc).isoformat()
                            },
                            technical_id=technical_id,
                            meta={}
                        )
            except Exception as e2:
                logger.exception(f"Failed to update weather_processing_jobs to failed: {e2}")

    asyncio.create_task(background_job(entity.copy()))

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
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert_obj,
            workflow=process_alert
        )
        return jsonify({"alert_id": alert_obj.get("alert_id"), "status": "active"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create alert"}), 500

@app.route("/alerts/<alert_id>", methods=["POST"])
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
            entity=job_entity,
            workflow=process_weather_processing_jobs
        )
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