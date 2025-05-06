```python
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from uuid import uuid4

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "databases"
users_alerts: Dict[str, List[Dict[str, Any]]] = {}
notifications_history: Dict[str, List[Dict[str, Any]]] = {}

# Job tracking for weather data processing
weather_processing_jobs: Dict[str, Dict[str, Any]] = {}

# Real external weather API config (Open-Meteo used as example)
# Docs: https://open-meteo.com/en/docs
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"


async def send_notification(user_id: str, alert_id: str, channel: str, target: str, message: str) -> bool:
    """
    Mock notification sender.
    TODO: Implement real email/SMS/webhook integrations.
    """
    try:
        logger.info(f"Sending notification to user {user_id} via {channel} to {target}: {message}")
        # Here you would integrate with real services (e.g. SMTP, Twilio, webhook POST)
        # For webhook example, we can do a POST if channel == 'webhook'
        if channel == "webhook":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(target, json={"alert_id": alert_id, "message": message})
                if resp.status_code >= 400:
                    logger.warning(f"Webhook notification failed: {resp.status_code} {resp.text}")
                    return False
        # For email/SMS just mock success
        return True
    except Exception as e:
        logger.exception(e)
        return False


async def evaluate_alerts_for_weather_data(location: str, timestamp: str, temperature: float, rain_forecast: bool):
    """
    Evaluate all alerts for all users against the incoming weather data.
    For each match, send notifications.
    """
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
                    # value expected as boolean string 'true'/'false' or bool
                    val_bool = (str(value).lower() == "true")
                    if op == "eq" and rain_forecast != val_bool:
                        matches = False
                else:
                    logger.warning(f"Unknown condition type: {ctype}")
                    matches = False

                if not matches:
                    break

            if matches:
                # Send notifications
                notification_channels = alert.get("notification_channels", [])
                notification_targets = alert.get("notification_targets", {})
                alert_id = alert["alert_id"]

                notification_results = []
                for channel in notification_channels:
                    target = notification_targets.get(channel)
                    if not target:
                        logger.warning(f"Missing notification target for channel {channel} in alert {alert_id}")
                        continue
                    message = f"Weather alert triggered for your rule '{alert['name']}' at {location}."
                    success = await send_notification(user_id, alert_id, channel, target, message)
                    notification_results.append({
                        "channel": channel,
                        "status": "sent" if success else "failed"
                    })

                    # Save notification history
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
        # Mark job as processing
        weather_processing_jobs[job_id]["status"] = "processing"

        location = data.get("location")
        timestamp = data.get("timestamp")
        temperature = data.get("temperature")
        rain_forecast = data.get("rain_forecast")

        # TODO: You could enrich weather data by calling external APIs here if needed.
        # For example, fetching forecast from Open-Meteo (optional)
        # For prototype, we assume data already includes necessary info.

        alerts_triggered = await evaluate_alerts_for_weather_data(location, timestamp, temperature, rain_forecast)

        weather_processing_jobs[job_id]["status"] = "completed"
        weather_processing_jobs[job_id]["alerts_triggered"] = alerts_triggered
        weather_processing_jobs[job_id]["processed_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.exception(e)
        weather_processing_jobs[job_id]["status"] = "failed"
        weather_processing_jobs[job_id]["error"] = str(e)


@app.route("/alerts", methods=["POST"])
async def create_alert():
    data = await request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    alert_id = str(uuid4())
    alert = {
        "alert_id": alert_id,
        "name": data.get("name", "Unnamed alert"),
        "conditions": data.get("conditions", []),
        "notification_channels": data.get("notification_channels", []),
        "notification_targets": data.get("notification_targets", {}),
        "status": "active"
    }

    users_alerts.setdefault(user_id, []).append(alert)
    return jsonify({"alert_id": alert_id, "status": "active"}), 201


@app.route("/alerts/<alert_id>", methods=["POST"])
async def update_alert(alert_id):
    data = await request.get_json()
    # Find alert by alert_id
    found = False
    for alerts in users_alerts.values():
        for alert in alerts:
            if alert["alert_id"] == alert_id:
                # Update fields
                if "name" in data:
                    alert["name"] = data["name"]
                if "conditions" in data:
                    alert["conditions"] = data["conditions"]
                if "notification_channels" in data:
                    alert["notification_channels"] = data["notification_channels"]
                if "notification_targets" in data:
                    alert["notification_targets"] = data["notification_targets"]
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


@app.route("/users/<user_id>/alerts", methods=["GET"])
async def get_user_alerts(user_id):
    alerts = users_alerts.get(user_id, [])
    # Return only active, paused, or deleted alerts as per spec
    return jsonify(alerts), 200


@app.route("/weather/data", methods=["POST"])
async def post_weather_data():
    data = await request.get_json()
    job_id = str(uuid4())
    requested_at = datetime.now(timezone.utc).isoformat()
    weather_processing_jobs[job_id] = {"status": "queued", "requestedAt": requested_at}

    # Fire and forget processing task
    asyncio.create_task(process_weather_data(job_id, data))

    return jsonify({"job_id": job_id, "status": "queued", "requestedAt": requested_at}), 200


@app.route("/users/<user_id>/notifications", methods=["GET"])
async def get_notifications(user_id):
    history = notifications_history.get(user_id, [])
    return jsonify(history), 200


if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```