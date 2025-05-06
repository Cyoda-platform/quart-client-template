from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
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

OPENWEATHER_API_KEY = "your_openweathermap_api_key"  # TODO: Replace with your actual API key
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

        # Retrieve all alerts
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

        # Update weather entity with alerts triggered
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


async def process_weather_fetch(entity):
    try:
        entity['weather_id'] = entity.get('weather_id') or str(uuid.uuid4())
        entity['created_at'] = entity.get('created_at') or datetime.utcnow().isoformat() + "Z"
        entity['status'] = 'processing'

        # Add initial weather entity with processing status
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity
        )

        weather_data = await fetch_weather(entity.get("location", {}), entity.get("data_type", "current"))
        entity['weather_data'] = weather_data
        entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"
        entity['status'] = 'completed'

        # Update weather entity with fetched data
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity['weather_id'],
            meta={}
        )

        await asyncio.create_task(process_alert_evaluation(entity['weather_id']))

    except Exception as e:
        logger.exception(e)
        entity['status'] = 'failed'
        entity['error'] = str(e)
        entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"

        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="weather",
                entity_version=ENTITY_VERSION,
                entity=entity,
                technical_id=entity.get('weather_id', 'unknown'),
                meta={}
            )
        except Exception as ex:
            logger.exception(ex)


@app.route("/alerts", methods=["POST"])
@validate_request(AlertRequest)  # POST validation must go last for workaround
async def create_or_update_alert(data: AlertRequest):
    try:
        alert = data.__dict__
        if not alert.get("user_id") or not alert.get("conditions"):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        alert_id = alert.get("alert_id") or str(uuid.uuid4())
        alert["alert_id"] = alert_id
        alert.setdefault("status", "active")

        # Check if alert exists
        existing_alert = None
        if alert.get("alert_id"):
            try:
                existing_alert = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="alert",
                    entity_version=ENTITY_VERSION,
                    technical_id=alert_id
                )
            except Exception:
                existing_alert = None

        if existing_alert:
            # Update alert
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="alert",
                entity_version=ENTITY_VERSION,
                entity=alert,
                technical_id=alert_id,
                meta={}
            )
        else:
            # Add new alert
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="alert",
                entity_version=ENTITY_VERSION,
                entity=alert
            )

        return jsonify({"status": "success", "alert_id": alert_id, "message": "Alert created/updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)  # POST validation must go last for workaround
async def weather_fetch(data: WeatherFetchRequest):
    try:
        entity = {
            "location": data.location,
            "data_type": data.data_type,
            "weather_id": str(uuid.uuid4()),
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z"
        }

        # Add initial weather entity with processing status
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather",
            entity_version=ENTITY_VERSION,
            entity=entity
        )

        asyncio.create_task(process_weather_fetch(entity))

        return jsonify({"status": "success", "weather_id": entity["weather_id"], "message": "Weather data fetch started and alerts evaluation triggered"})
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
        return jsonify([])  # Return empty list on error


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)