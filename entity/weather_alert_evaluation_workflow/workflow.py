import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_evaluate_alert_rules(entity: dict):
    try:
        alert_rules = []  # TODO: Fetch active AlertRule entities matching entity location

        triggered_alerts = []
        for alert_rule in alert_rules:
            condition_met = False
            if alert_rule["condition_type"] == "temperature_above":
                temp = entity.get("weather_data", {}).get("main", {}).get("temp")
                if temp is not None and temp > alert_rule["threshold_value"]:
                    condition_met = True
            elif alert_rule["condition_type"] == "temperature_below":
                temp = entity.get("weather_data", {}).get("main", {}).get("temp")
                if temp is not None and temp < alert_rule["threshold_value"]:
                    condition_met = True
            elif alert_rule["condition_type"] == "rain_forecast":
                weather = entity.get("weather_data", {}).get("weather", [])
                if any("rain" in w.get("description", "").lower() for w in weather):
                    condition_met = True
            # Add other condition types as needed

            if condition_met:
                triggered_alerts.append(alert_rule)

        entity["triggered_alerts"] = triggered_alerts
        entity["alert_evaluation_status"] = "evaluated"
        entity["evaluated_at"] = datetime.utcnow().isoformat()
        logger.info(f"Alert evaluation completed for request_id={entity.get('request_id')}, triggered {len(triggered_alerts)} alerts")
    except Exception as e:
        entity["alert_evaluation_status"] = "failed"
        entity["error_message"] = str(e)
        logger.exception("Error in process_evaluate_alert_rules")
    return entity

async def process_send_notifications(entity: dict):
    try:
        triggered_alerts = entity.get("triggered_alerts", [])
        for alert_rule in triggered_alerts:
            method = alert_rule.get("notification_method")
            contact = alert_rule.get("contact_info")
            message = f"Weather alert triggered: {alert_rule['condition_type']} threshold {alert_rule['threshold_value']} met."

            if method == "email":
                # TODO: Integrate with email sending service
                logger.info(f"Sending email to {contact}: {message}")
            elif method == "sms":
                # TODO: Integrate with SMS sending service
                logger.info(f"Sending SMS to {contact}: {message}")
            elif method == "webhook":
                # TODO: Integrate with webhook POST
                logger.info(f"Calling webhook {contact} with message: {message}")
            else:
                logger.warning(f"Unknown notification method {method} for alert_rule")

        entity["notification_status"] = "sent"
        entity["notified_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        entity["notification_status"] = "failed"
        entity["error_message"] = str(e)
        logger.exception("Error in process_send_notifications")
    return entity