import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

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

@app.route("/events/detect", methods=["POST"])
# Workaround: validate_request placed last for POST due to quart-schema issue
@validate_request(EventDetect)
async def events_detect(data: EventDetect):
    asyncio.create_task(process_event(data.__dict__))
    if data.event_type == "food_request" and data.intensity == "dramatic":
        return jsonify({"status": "success", "message": "Notification sent"})
    return jsonify({"status": "success", "message": "No notification needed"})

@app.route("/notifications", methods=["GET"])
async def get_notifications():
    return jsonify({"notifications": notifications_cache})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)