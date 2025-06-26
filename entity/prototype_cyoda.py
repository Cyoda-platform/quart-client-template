from dataclasses import dataclass
import asyncio
import base64
import datetime
import logging
from typing import Dict, List
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

# We will no longer use local caches for events and notifications

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

async def send_notification(cat_id: str, event_type: str, message: str) -> Dict:
    notification = {
        "cat_id": cat_id,
        "event_type": event_type,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    try:
        # add notification via entity_service (entity name 'notification')
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="notification",
            entity_version=ENTITY_VERSION,
            entity=notification
        )
        logger.info("Notification enqueued with id: %s", id)
        return {"status": "success", "details": "Notification enqueued", "id": id}
    except Exception:
        logger.exception("Failed to enqueue notification")
        return {"status": "failure", "details": "Internal server error"}

async def process_event(cat_id: str, input_type: str, input_data: str):
    detected = False
    if input_type == "text":
        detected = await detect_food_request_from_text(input_data)
    elif input_type == "audio":
        detected = await detect_food_request_from_audio(input_data)
    if detected:
        event = {
            "cat_id": cat_id,
            "event_type": "food_request",
            "message": "Emergency! A cat demands snacks",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        try:
            # Save event via entity_service (entity name 'event')
            event_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="event",
                entity_version=ENTITY_VERSION,
                entity=event
            )
            await send_notification(cat_id, event["event_type"], event["message"])
            return {"event_detected": True, "event_type": event["event_type"], "message": event["message"], "id": event_id}
        except Exception:
            logger.exception("Failed to add event")
            return {"event_detected": False, "event_type": None, "message": "Failed to add event"}
    return {"event_detected": False, "event_type": None, "message": "No key event detected"}

@app.route("/events/detect", methods=["POST"])
@validate_request(DetectEventRequest)
async def detect_event(data: DetectEventRequest):
    try:
        result = await process_event(data.cat_id, data.input_type, data.input_data)
        return jsonify(result)
    except Exception:
        logger.exception("Event detection failed")
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
    try:
        result = await send_notification(data.cat_id, data.event_type, data.message)
        return jsonify(result)
    except Exception:
        logger.exception("Notification send failed")
        return jsonify({"status": "failure", "details": "Internal server error"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)