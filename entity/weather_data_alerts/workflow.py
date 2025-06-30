async def evaluate_alert_conditions(entity: dict):
    # Example logic: check if temperature exceeds threshold or severe weather condition
    alert_conditions = entity.get("alert_conditions", {})
    weather_data = entity.get("weather_data", {})
    alerts_triggered = []
    for condition, threshold in alert_conditions.items():
        value = weather_data.get(condition)
        if value is not None and value >= threshold:
            alerts_triggered.append(condition)
    entity["alerts_triggered"] = alerts_triggered
    entity["alert_active"] = len(alerts_triggered) > 0
    entity["workflowProcessed"] = True

async def send_notification(entity: dict):
    if not entity.get("alert_active"):
        return
    notifications = entity.setdefault("notifications", [])
    alerts = entity.get("alerts_triggered", [])
    for alert in alerts:
        notification = {
            "type": alert,
            "message": f"Alert triggered for {alert}",
            "timestamp": entity.get("timestamp"),
        }
        notifications.append(notification)
    entity["notifications_sent"] = len(alerts)
    entity["workflowProcessed"] = True

async def log_alert_dispatch(entity: dict):
    if not entity.get("alert_active"):
        return
    logs = entity.setdefault("logs", [])
    alerts = entity.get("alerts_triggered", [])
    for alert in alerts:
        log_entry = {
            "event": "alert_dispatched",
            "alert_type": alert,
            "timestamp": entity.get("timestamp"),
            "details": f"Notification sent for alert: {alert}"
        }
        logs.append(log_entry)
    entity["logs_recorded"] = len(alerts)
    entity["workflowProcessed"] = True