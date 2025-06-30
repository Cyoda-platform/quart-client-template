async def evaluate_alert_conditions(entity: dict):
    conditions = entity.get("conditions", {})
    weather_data = entity.get("weather_data", {})
    alerts_triggered = []
    rain_forecast = conditions.get("rain_forecast")
    if rain_forecast is not None:
        if weather_data.get("rain_forecast", False) == rain_forecast:
            alerts_triggered.append("rain_forecast")
    temp_above = conditions.get("temperature_above")
    if temp_above is not None:
        if weather_data.get("temperature", float("-inf")) > temp_above:
            alerts_triggered.append("temperature_above")
    temp_below = conditions.get("temperature_below")
    if temp_below is not None:
        if weather_data.get("temperature", float("inf")) < temp_below:
            alerts_triggered.append("temperature_below")
    entity["alerts_triggered"] = alerts_triggered
    entity["alert_active"] = len(alerts_triggered) > 0
    entity["workflowProcessed"] = True

async def send_notification(entity: dict):
    if not entity.get("alert_active"):
        return
    notifications = entity.setdefault("notifications", [])
    prefs = entity.get("notification_preferences", {})
    for alert in entity.get("alerts_triggered", []):
        notification = {
            "alert": alert,
            "email": prefs.get("email"),
            "sms": prefs.get("sms"),
            "webhook": prefs.get("webhook"),
            "message": f"Alert triggered: {alert}",
            "timestamp": entity.get("updated_at"),
        }
        notifications.append(notification)
    entity["notifications_sent"] = len(entity.get("alerts_triggered", []))
    entity["workflowProcessed"] = True

async def log_alert_dispatch(entity: dict):
    if not entity.get("alert_active"):
        return
    logs = entity.setdefault("logs", [])
    for alert in entity.get("alerts_triggered", []):
        logs.append({
            "event": "alert_dispatched",
            "alert": alert,
            "timestamp": entity.get("updated_at"),
            "details": f"Notification sent for alert {alert}"
        })
    entity["logs_recorded"] = len(entity.get("alerts_triggered", []))
    entity["workflowProcessed"] = True