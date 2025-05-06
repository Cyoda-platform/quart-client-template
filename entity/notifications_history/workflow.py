import asyncio
import logging
from typing import Dict, Any

import httpx

logger = logging.getLogger(__name__)


async def process_send_notification(entity: Dict[str, Any]) -> None:
    user_id = entity.get("user_id")
    alert_id = entity.get("alert_id")
    channel = entity.get("channel")
    if not all([user_id, alert_id, channel]):
        logger.warning("Missing fields for notifications_history entity, skipping send")
        entity["status"] = "failed"
        return
    target = entity.get("target")
    if not target:
        logger.warning("No target found in notifications_history entity, skipping send")
        entity["status"] = "failed"
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
                    return
        entity["status"] = "sent"
    except Exception as e:
        logger.exception(f"Failed to send notification: {e}")
        entity["status"] = "failed"


async def process_evaluate_conditions(entity: Dict[str, Any]) -> None:
    # entity must contain weather data and user alerts
    # Evaluate alert conditions and prepare notifications entities
    alerts_triggered = []
    weather_data = entity.get("weather_data", {})
    users_alerts = entity.get("users_alerts", {})
    temperature = weather_data.get("temperature")
    rain_forecast = weather_data.get("rain_forecast")
    location = weather_data.get("location")
    timestamp = weather_data.get("timestamp")

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
                for channel in notification_channels:
                    target = notification_targets.get(channel)
                    if not target:
                        logger.warning(f"Missing notification target for channel {channel} in alert {alert_id}")
                        continue
                    notification_entity = {
                        "user_id": user_id,
                        "alert_id": alert_id,
                        "channel": channel,
                        "target": target,
                        "message": f"Weather alert triggered for your rule '{alert['name']}' at {location}.",
                        "status": "pending",
                        "timestamp": timestamp,
                    }
                    alerts_triggered.append(notification_entity)
    entity["alerts_triggered"] = alerts_triggered