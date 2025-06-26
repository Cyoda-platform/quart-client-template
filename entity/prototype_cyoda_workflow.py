from dataclasses import dataclass
import asyncio
import base64
import datetime
import logging
from typing import Dict
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

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
class DetectEventRequest:
    cat_id: str
    input_type: str
    input_data: str

@dataclass
class NotificationRequest:
    cat_id: str
    event_type: str
    message: str

async def detect_food_request_from_text(text: str) -> bool:
    keywords = ["snack", "food", "hungry", "feed", "treat", "meow", "demand"]
    return any(k in text.lower() for k in keywords)

async def detect_food_request_from_audio(audio_b64: str) -> bool:
    ASSEMBLYAI_API_KEY = "YOUR_ASSEMBLYAI_API_KEY"  # TODO: Add your AssemblyAI API key
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            audio_bytes = base64.b64decode(audio_b64)
            upload_resp = await client.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": ASSEMBLYAI_API_KEY},
                content=audio_bytes,
            )
            upload_resp.raise_for_status()
            upload_url = upload_resp.json()["upload_url"]
            transcript_req = {"audio_url": upload_url, "language_code": "en", "iab_categories": False}
            tr_resp = await client.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"},
                json=transcript_req,
            )
            tr_resp.raise_for_status()
            tid = tr_resp.json()["id"]
            while True:
                status_resp = await client.get(
                    f"https://api.assemblyai.com/v2/transcript/{tid}",
                    headers={"authorization": ASSEMBLYAI_API_KEY},
                )
                status_resp.raise_for_status()
                st = status_resp.json()
                if st["status"] == "completed":
                    text = st["text"]
                    break
                if st["status"] == "error":
                    logger.error("AssemblyAI error: %s", st.get("error"))
                    return False
                await asyncio.sleep(2)
            return await detect_food_request_from_text(text)
        except Exception:
            logger.exception("Audio detection failed")
            return False

async def send_notification_entity(cat_id: str, event_type: str, message: str):
    notification = {
        "cat_id": cat_id,
        "event_type": event_type,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="notification",
            entity_version=ENTITY_VERSION,
            entity=notification,
            workflow=process_notification
        )
        logger.info("Notification entity added asynchronously.")
    except Exception:
        logger.exception("Failed to add notification entity asynchronously.")

async def process_event(entity: dict) -> None:
    entity["processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    input_type = entity.get("input_type")
    input_data = entity.get("input_data")
    cat_id = entity.get("cat_id")

    if not (cat_id and input_type and input_data):
        logger.warning("Event entity missing required fields for processing.")
        return

    detected = False
    try:
        if input_type == "text":
            detected = await detect_food_request_from_text(input_data)
        elif input_type == "audio":
            detected = await detect_food_request_from_audio(input_data)
    except Exception:
        logger.exception("Failed to detect food request in process_event")

    if detected:
        entity["event_type"] = "food_request"
        entity["message"] = "Emergency! A cat demands snacks"
        # Fire-and-forget notification creation
        asyncio.create_task(
            send_notification_entity(cat_id, entity["event_type"], entity["message"])
        )
    else:
        entity["event_type"] = None
        entity["message"] = None

async def process_notification(entity: dict) -> None:
    if "timestamp" not in entity:
        entity["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    entity.setdefault("priority", "normal")

@app.route("/events/detect", methods=["POST"])
@validate_request(DetectEventRequest)
async def detect_event(data: DetectEventRequest):
    event = {
        "cat_id": data.cat_id,
        "input_type": data.input_type,
        "input_data": data.input_data,
    }
    try:
        event_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="event",
            entity_version=ENTITY_VERSION,
            entity=event,
            workflow=process_event
        )
        return jsonify({"id": event_id})
    except Exception:
        logger.exception("Failed to add event")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/events/<string:cat_id>", methods=["GET"])
async def get_events(cat_id):
    try:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.cat_id",
                        "operatorType": "EQUALS",
                        "value": cat_id,
                        "type": "simple"
                    }
                ]
            }
        }
        events = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="event",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify(events)
    except Exception:
        logger.exception("Failed to get events")
        return jsonify([])

@app.route("/notifications/send", methods=["POST"])
@validate_request(NotificationRequest)
async def notifications_send(data: NotificationRequest):
    notification = {
        "cat_id": data.cat_id,
        "event_type": data.event_type,
        "message": data.message,
    }
    try:
        notification_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="notification",
            entity_version=ENTITY_VERSION,
            entity=notification,
            workflow=process_notification
        )
        return jsonify({"id": notification_id})
    except Exception:
        logger.exception("Failed to add notification")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)