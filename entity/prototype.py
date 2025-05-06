from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "databases"
users_alerts: Dict[str, List[Dict[str, Any]]] = {}
notifications_history: Dict[str, List[Dict[str, Any]]] = {}
weather_processing_jobs: Dict[str, Dict[str, Any]] = {}

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
    for user_id, alerts in users_alerts.items():
        for alert in alerts:
            if alert.get("status") != "active":
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
                        logger.warning(f"Invalid temperature condition in alert {alert['alert_id']}: {e}")
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
                alert_id = alert["alert_id"]
                notification_results = []
                for channel in notification_channels:
                    target = getattr(notification_targets, channel, None) if isinstance(notification_targets, NotificationTargets) else notification_targets.get(channel)
                    if not target:
                        logger.warning(f"Missing notification target for channel {channel} in alert {alert_id}")
                        continue
                    message = f"Weather alert triggered for your rule '{alert['name']}' at {location}."
                    success = await send_notification(user_id, alert_id, channel, target, message)
                    notification_results.append({
                        "channel": channel,
                        "status": "sent" if success else "failed"
                    })
                    notifications_history.setdefault(user_id, []).append({
                        "notification_id": str(uuid4()),
                        "alert_id": alert_id,
                        "channel": channel,
                        "status": "sent" if success else "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                alerts_triggered.append({
                    "alert_id": alert_id,
                    "user_id": user_id,
                    "notification_channels": [r["channel"] for r in notification_results],
                    "notification_status": "sent" if all(r["status"] == "sent" for r in notification_results) else "failed"
                })
    return alerts_triggered

async def process_weather_data(job_id: str, data: Dict[str, Any]):
    try:
        weather_processing_jobs[job_id]["status"] = "processing"
        location = data.get("location")
        timestamp = data.get("timestamp")
        temperature = data.get("temperature")
        rain_forecast = data.get("rain_forecast")
        alerts_triggered = await evaluate_alerts_for_weather_data(location, timestamp, temperature, rain_forecast)
        weather_processing_jobs[job_id]["status"] = "completed"
        weather_processing_jobs[job_id]["alerts_triggered"] = alerts_triggered
        weather_processing_jobs[job_id]["processed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.exception(e)
        weather_processing_jobs[job_id]["status"] = "failed"
        weather_processing_jobs[job_id]["error"] = str(e)

# POST routes with @validate_request last (workaround issue)
@app.route("/alerts", methods=["POST"])
@validate_request(CreateAlertRequest)
async def create_alert(data: CreateAlertRequest):
    alert_id = str(uuid4())
    alert = {
        "alert_id": alert_id,
        "name": data.name,
        "conditions": [cond.__dict__ for cond in data.conditions],
        "notification_channels": data.notification_channels,
        "notification_targets": data.notification_targets.__dict__ if data.notification_targets else {},
        "status": "active"
    }
    users_alerts.setdefault(data.user_id, []).append(alert)
    return jsonify({"alert_id": alert_id, "status": "active"}), 201

@app.route("/alerts/<alert_id>", methods=["POST"])
@validate_request(UpdateAlertRequest)
async def update_alert(data: UpdateAlertRequest, alert_id):
    found = False
    for alerts in users_alerts.values():
        for alert in alerts:
            if alert["alert_id"] == alert_id:
                if data.name is not None:
                    alert["name"] = data.name
                if data.conditions is not None:
                    alert["conditions"] = [cond.__dict__ for cond in data.conditions]
                if data.notification_channels is not None:
                    alert["notification_channels"] = data.notification_channels
                if data.notification_targets is not None:
                    alert["notification_targets"] = data.notification_targets.__dict__
                found = True
                break
        if found:
            break
    if not found:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"alert_id": alert_id, "status": "updated"}), 200

@app.route("/alerts/<alert_id>/delete", methods=["POST"])
async def delete_alert(alert_id):
    found = False
    for alerts in users_alerts.values():
        for alert in alerts:
            if alert["alert_id"] == alert_id:
                alert["status"] = "deleted"
                found = True
                break
        if found:
            break
    if not found:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"alert_id": alert_id, "status": "deleted"}), 200

# GET routes with @validate_querystring first (workaround issue)
# No query parameters for these GET routes, so no validation needed
@app.route("/users/<user_id>/alerts", methods=["GET"])
async def get_user_alerts(user_id):
    alerts = users_alerts.get(user_id, [])
    return jsonify(alerts), 200

@app.route("/weather/data", methods=["POST"])
@validate_request(WeatherDataRequest)
async def post_weather_data(data: WeatherDataRequest):
    job_id = str(uuid4())
    requested_at = datetime.now(timezone.utc).isoformat()
    weather_processing_jobs[job_id] = {"status": "queued", "requestedAt": requested_at}
    asyncio.create_task(process_weather_data(job_id, data.__dict__))
    return jsonify({"job_id": job_id, "status": "queued", "requestedAt": requested_at}), 200

@app.route("/users/<user_id>/notifications", methods=["GET"])
async def get_notifications(user_id):
    history = notifications_history.get(user_id, [])
    return jsonify(history), 200

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```