import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class EventDetect:
    event_type: str
    intensity: str
    timestamp: str

notifications_cache: List[Dict[str, Any]] = []

NOTIFICATION_API_URL = "https://httpbin.org/post"

async def send_notification(message: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(NOTIFICATION_API_URL, json={"message": message})
            resp.raise_for_status()
            logger.info(f"Notification sent: {message}")
            return True
        except Exception as e:
            logger.exception(f"Failed to send notification: {e}")
            return False

async def process_event(data: Dict[str, Any]):
    event_type = data.get("event_type")
    intensity = data.get("intensity")
    timestamp = data.get("timestamp")
    try:
        event_time = datetime.fromisoformat(timestamp)
    except Exception as e:
        logger.warning(f"Invalid timestamp format: {timestamp}, error: {e}")
        event_time = datetime.utcnow()

    if event_type == "food_request" and intensity == "dramatic":
        message = "Emergency! A cat demands snacks"
        sent = await send_notification(message)
        if sent:
            notifications_cache.append({"timestamp": event_time.isoformat(), "message": message})
    else:
        logger.info(f"No notification needed for event_type={event_type}, intensity={intensity}")

entity_name = "event_detect"  # underscore lowercase entity name

@app.route("/events/detect", methods=["POST"])
# Workaround: validate_request placed last for POST due to quart-schema issue
@validate_request(EventDetect)
async def events_detect(data: EventDetect):
    data_dict = data.__dict__
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        asyncio.create_task(process_event(data_dict))
        return jsonify({"id": str(id)})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add event"}), 500

@app.route("/events/detect/<string:id>", methods=["GET"])
async def get_event_detect(id: str):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        if item is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(item)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve event"}), 500

@app.route("/events/detect", methods=["GET"])
async def list_event_detects():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        return jsonify(items)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to list events"}), 500

@app.route("/events/detect/<string:id>", methods=["PUT"])
@validate_request(EventDetect)
async def update_event_detect(id: str, data: EventDetect):
    data_dict = data.__dict__
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            technical_id=id,
            meta={}
        )
        return jsonify({"status": "updated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update event"}), 500

@app.route("/events/detect/<string:id>", methods=["DELETE"])
async def delete_event_detect(id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=id,
            meta={}
        )
        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete event"}), 500

@app.route("/notifications", methods=["GET"])
async def get_notifications():
    return jsonify({"notifications": notifications_cache})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)