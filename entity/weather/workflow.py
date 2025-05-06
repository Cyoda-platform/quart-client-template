import logging
import uuid
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OPENWEATHER_API_KEY = "your_openweathermap_api_key"  # Replace with your actual API key
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def process_fetch_weather(entity):
    location = entity.get("location", {})
    data_type = entity.get("data_type", "current")
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have city or latitude and longitude")

    endpoint = "/weather" if data_type == "current" else "/forecast"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}{endpoint}", params=params)
        resp.raise_for_status()
        entity['weather_data'] = resp.json()


async def process_evaluate_alerts(entity):
    # TODO: Replace entity_service calls with internal logic or mocks
    try:
        # Mock retrieval of alerts for prototype
        all_alerts = entity.get("alerts", [])

        location = entity.get("location", {})
        weather_data = entity.get("weather_data", {})
        alerts_triggered = []

        for alert in all_alerts:
            alert_id = alert.get("alert_id")
            if alert.get("location") != location or alert.get("status") != "active":
                continue

            triggered_conditions = []
            for cond in alert.get("conditions", []):
                try:
                    condition_type = cond.get("condition_type")
                    operator = cond.get("operator")
                    threshold = cond.get("threshold")

                    if condition_type == "temperature":
                        actual = weather_data.get("main", {}).get("temp")
                    elif condition_type == "rain":
                        rain_info = weather_data.get("rain", {})
                        actual = rain_info.get("1h", 0) or rain_info.get("3h", 0) or 0
                    else:
                        logger.warning(f"Unsupported condition_type: {condition_type}")
                        continue

                    if actual is None:
                        continue

                    met = False
                    if operator == "greater_than":
                        met = actual > threshold
                    elif operator == "less_than":
                        met = actual < threshold
                    elif operator == "equals":
                        met = actual == threshold

                    if met:
                        triggered_conditions.append(cond)
                except Exception as e:
                    logger.exception(f"Error evaluating alert condition: {e}")

            if triggered_conditions:
                logger.info(f"Alert {alert_id} triggered for weather {entity.get('weather_id')} with conditions: {triggered_conditions}")
                alerts_triggered.append({
                    "alert_id": alert_id,
                    "triggered_conditions": triggered_conditions,
                    "notification_status": "sent"
                })

        entity["alerts_triggered"] = alerts_triggered
    except Exception as e:
        logger.exception(e)