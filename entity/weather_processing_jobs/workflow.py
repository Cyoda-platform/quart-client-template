import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4
import httpx

logger = logging.getLogger(__name__)

async def process_fetch_active_alerts(entity: Dict[str, Any]) -> None:
    # TODO: Replace with actual fetching logic or mock data
    # For prototype, simulate fetching active alerts from entity
    # Assuming entity["active_alerts"] is set externally before orchestration
    pass  # no changes to entity here

async def process_evaluate_alerts(entity: Dict[str, Any]) -> None:
    weather_data = entity.get("weather_data", {})
    temperature = weather_data.get("temperature")
    rain_forecast = weather_data.get("rain_forecast")
    location = weather_data.get("location")
    timestamp = weather_data.get("timestamp")

    active_alerts = entity.get("active_alerts", [])
    alerts_triggered = []

    for alert in active_alerts:
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
            user_id = alert.get("user_id")
            for channel in notification_channels:
                target = None
                if isinstance(notification_targets, dict):
                    target = notification_targets.get(channel)
                else:
                    target = getattr(notification_targets, channel, None)
                if not target:
                    logger.warning(f"Missing notification target for channel {channel} in alert {alert_id}")
                    continue
                notification_entity = {
                    "notification_id": str(uuid4()),
                    "alert_id": alert_id,
                    "channel": channel,
                    "status": "pending",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "target": target,
                    "message": f"Weather alert triggered for your rule '{alert.get('name')}' at {location}."
                }
                alerts_triggered.append(notification_entity)
    entity["alerts_triggered"] = alerts_triggered

async def process_send_notifications(entity: Dict[str, Any]) -> None:
    notifications = entity.get("alerts_triggered", [])
    async def send_single(notification: Dict[str, Any]) -> None:
        channel = notification.get("channel")
        target = notification.get("target")
        alert_id = notification.get("alert_id")
        user_id = notification.get("user_id")
        message = notification.get("message", f"Alert {alert_id} triggered")
        if not all([channel, target, alert_id, user_id]):
            logger.warning("Notification missing required fields, skipping send")
            notification["status"] = "failed"
            return
        try:
            logger.info(f"Sending notification via {channel} to {target} for user {user_id}")
            if channel == "webhook":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(target, json={"alert_id": alert_id, "message": message})
                    if resp.status_code >= 400:
                        logger.warning(f"Webhook notification failed: {resp.status_code} {resp.text}")
                        notification["status"] = "failed"
                        return
            notification["status"] = "sent"
        except Exception as e:
            logger.exception(f"Failed to send notification: {e}")
            notification["status"] = "failed"
    await asyncio.gather(*(send_single(n) for n in notifications))

async def process_update_job_status(entity: Dict[str, Any]) -> None:
    # Update job status based on notifications send result
    alerts_triggered = entity.get("alerts_triggered", [])
    if not alerts_triggered:
        entity["status"] = "completed"
        entity["alerts_report"] = []
        entity["processed_at"] = datetime.now(timezone.utc).isoformat()
        return
    status = "completed"
    report = []
    for alert in alerts_triggered:
        channels_status = alert.get("status", "sent") if "status" in alert else None
        if channels_status == "failed":
            status = "failed"
        report.append({
            "alert_id": alert.get("alert_id"),
            "user_id": alert.get("user_id"),
            "channel": alert.get("channel"),
            "status": alert.get("status")
        })
    entity["status"] = status
    entity["alerts_report"] = report
    entity["processed_at"] = datetime.now(timezone.utc).isoformat()