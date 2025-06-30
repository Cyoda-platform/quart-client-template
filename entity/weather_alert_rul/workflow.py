async def evaluate_alert_conditions(entity: dict):
    alert_rules = entity.get("alert_rules", [])
    weather_data = entity.get("weather_data", {})
    triggered_alerts = []
    for rule in alert_rules:
        parameter = rule.get("parameter")
        threshold = rule.get("threshold")
        condition = rule.get("condition")
        value = weather_data.get(parameter)
        if value is None:
            continue
        if condition == "greater_than" and value > threshold:
            triggered_alerts.append(rule)
        elif condition == "less_than" and value < threshold:
            triggered_alerts.append(rule)
        elif condition == "equal_to" and value == threshold:
            triggered_alerts.append(rule)
    entity["triggered_alerts"] = triggered_alerts
    entity["alert_active"] = len(triggered_alerts) > 0
    entity["workflowProcessed"] = True

async def send_notification(entity: dict):
    if not entity.get("alert_active"):
        return
    notifications = entity.setdefault("notifications", [])
    for alert in entity.get("triggered_alerts", []):
        notification = {
            "alert_id": alert.get("id"),
            "message": f"Alert triggered for {alert.get('parameter')} with condition {alert.get('condition')} {alert.get('threshold')}",
            "sent_at": entity.get("timestamp")
        }
        notifications.append(notification)
    entity["notifications_sent"] = len(entity.get("triggered_alerts", []))
    entity["workflowProcessed"] = True

async def log_alert_dispatch(entity: dict):
    if not entity.get("alert_active"):
        return
    logs = entity.setdefault("logs", [])
    for alert in entity.get("triggered_alerts", []):
        log_entry = {
            "event": "alert_dispatched",
            "alert_id": alert.get("id"),
            "timestamp": entity.get("timestamp"),
            "details": f"Notification sent for alert {alert.get('id')} on parameter {alert.get('parameter')}"
        }
        logs.append(log_entry)
    entity["logs_recorded"] = len(entity.get("triggered_alerts", []))
    entity["workflowProcessed"] = True