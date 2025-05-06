from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class AlertCondition:
    condition_type: str
    operator: str
    threshold: float or bool

@dataclass
class NotificationDetails:
    email: str = None
    sms: str = None
    webhook_url: str = None

@dataclass
class AlertRequest:
    alert_id: str = None
    user_id: str = None
    location: dict = None
    conditions: list = None
    notification_channels: list = None
    notification_details: NotificationDetails = None
    message_template: str = None

@dataclass
class WeatherFetchRequest:
    location: dict
    data_type: str

OPENWEATHER_API_KEY = "your_openweathermap_api_key"  # Replace with your actual API key
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

async def fetch_weather(location, data_type):
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
        return resp.json()

async def process_alert_evaluation(weather_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            technical_id=weather_id
        )
        if not entity:
            logger.error(f"Weather data not found for id: {weather_id}")
            return

        location = entity.get("location", {})
        weather_data = entity.get("weather_data", {})
        alerts_triggered = []

        all_alerts = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
        )

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
                logger.info(f"Alert {alert_id} triggered for weather {weather_id} with conditions: {triggered_conditions}")
                alerts_triggered.append({
                    "alert_id": alert_id,
                    "triggered_conditions": triggered_conditions,
                    "notification_status": "sent"
                })

        entity["alerts_triggered"] = alerts_triggered

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=weather_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)

async def process_weather(entity):
    try:
        entity['weather_id'] = entity.get('weather_id') or str(uuid.uuid4())
        entity['created_at'] = entity.get('created_at') or datetime.utcnow().isoformat() + "Z"
        entity['status'] = 'processing'

        location = entity.get("location", {})
        data_type = entity.get("data_type", "current")

        weather_data = await fetch_weather(location, data_type)
        entity['weather_data'] = weather_data
        entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"
        entity['status'] = 'completed'

        # Trigger alert evaluation as a secondary entity add (allowed because different entity_model)
        # Use fire-and-forget to not block workflow persistence
        import asyncio
        asyncio.create_task(process_alert_evaluation(entity['weather_id']))

    except Exception as e:
        logger.exception(f"Error in process_weather for id={entity.get('weather_id')}: {e}")
        entity['status'] = 'failed'
        entity['error'] = str(e)
        entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"

    return entity

async def process_alert(entity):
    entity['alert_id'] = entity.get('alert_id') or str(uuid.uuid4())
    entity.setdefault('status', 'active')
    return entity

@app.route("/alerts", methods=["POST"])
@validate_request(AlertRequest)
async def create_or_update_alert(data: AlertRequest):
    try:
        alert = data.__dict__

        # Only prepare alert entity, persistence and workflow will handle id/status
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            entity=alert,
            workflow=process_alert
        )

        return jsonify({"status": "success", "alert_id": alert.get("alert_id"), "message": "Alert created/updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    try:
        entity = {
            "location": data.location,
            "data_type": data.data_type,
            "weather_id": str(uuid.uuid4()),
            "status": "queued",
            "requestedAt": datetime.utcnow().isoformat() + "Z"
        }

        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_weather
        )

        return jsonify({"status": "success", "weather_id": entity["weather_id"], "message": "Weather data fetch initiated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/weather/<weather_id>", methods=["GET"])
async def get_weather(weather_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            technical_id=weather_id
        )
        if not entity:
            return jsonify({"status": "error", "message": "weather_id not found"}), 404

        status = entity.get("status")
        if status in ("processing", "queued"):
            return jsonify({
                "weather_id": weather_id,
                "status": status,
                "message": "Data is being fetched, please try again later",
            }), 202

        if status == "failed":
            return jsonify({
                "weather_id": weather_id,
                "status": "failed",
                "error": entity.get("error", "Unknown error"),
            }), 500

        return jsonify(entity)
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/alerts/<user_id>", methods=["GET"])
async def get_user_alerts(user_id):
    try:
        condition = {"user_id": user_id}
        user_alerts = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="alert",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify(user_alerts)
    except Exception as e:
        logger.exception(e)
        return jsonify([])

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)