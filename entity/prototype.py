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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class DetectEventRequest:
    catId: str
    inputType: str
    inputData: str

@dataclass
class NotificationRequest:
    catId: str
    eventType: str
    message: str

# In-memory cache for events: catId -> List[events]
_events_cache: Dict[str, List[Dict]] = {}
# In-memory queue-like store for notifications (for demo purposes)
_notifications_cache: List[Dict] = []

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
        "catId": cat_id,
        "eventType": event_type,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    _notifications_cache.append(notification)
    logger.info("Notification sent: %s", notification)
    return {"status": "success", "details": "Notification enqueued"}

async def process_event(cat_id: str, input_type: str, input_data: str):
    detected = False
    if input_type == "text":
        detected = await detect_food_request_from_text(input_data)
    elif input_type == "audio":
        detected = await detect_food_request_from_audio(input_data)
    if detected:
        event = {
            "eventId": str(uuid4()),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "eventType": "food_request",
            "message": "Emergency! A cat demands snacks",
        }
        _events_cache.setdefault(cat_id, []).append(event)
        await send_notification(cat_id, event["eventType"], event["message"])
        return {"eventDetected": True, "eventType": event["eventType"], "message": event["message"]}
    return {"eventDetected": False, "eventType": None, "message": "No key event detected"}

@app.route("/events/detect", methods=["POST"])
@validate_request(DetectEventRequest)  # validation last for POST (workaround for quart-schema issue)
async def detect_event(data: DetectEventRequest):
    try:
        result = await process_event(data.catId, data.inputType, data.inputData)
        return jsonify(result)
    except Exception:
        logger.exception("Event detection failed")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/events/<string:cat_id>", methods=["GET"])
async def get_events(cat_id):
    events = _events_cache.get(cat_id, [])
    return jsonify(events)

@app.route("/notifications/send", methods=["POST"])
@validate_request(NotificationRequest)  # validation last for POST (workaround for quart-schema issue)
async def notifications_send(data: NotificationRequest):
    try:
        result = await send_notification(data.catId, data.eventType, data.message)
        return jsonify(result)
    except Exception:
        logger.exception("Notification send failed")
        return jsonify({"status": "failure", "details": "Internal server error"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)