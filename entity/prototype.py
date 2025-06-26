import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CatEvent:
    catId: Optional[str] = None
    eventType: str
    intensity: str

class AsyncCache:
    def __init__(self):
        self._storage = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._storage[key] = value

    async def get(self, key: str):
        async with self._lock:
            return self._storage.get(key)

    async def all(self):
        async with self._lock:
            return dict(self._storage)

events_cache = AsyncCache()
notifications_cache = AsyncCache()

NOTIFICATION_WEBHOOK_URL = "https://httpbin.org/post"

async def send_notification(message: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            payload = {"message": message}
            response = await client.post(NOTIFICATION_WEBHOOK_URL, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Notification sent: {message}")
            return True
        except Exception as e:
            logger.exception(f"Failed to send notification: {e}")
            return False

async def process_cat_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    event_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    event_id = f"event-{int(datetime.now().timestamp() * 1000)}"
    await events_cache.set(event_id, event_data)

    notification_sent = False
    notification_message = ""

    if event_data.get("eventType") == "food_request" and event_data.get("intensity", "").lower() == "dramatic":
        notification_message = "Emergency! A cat demands snacks"
        notification_sent = await send_notification(notification_message)
        notification_id = f"notif-{int(datetime.now().timestamp() * 1000)}"
        notification_record = {
            "id": notification_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": notification_message,
        }
        await notifications_cache.set(notification_id, notification_record)

    return {
        "notificationSent": notification_sent,
        "message": notification_message,
        "eventProcessed": event_data,
    }

@app.route("/events/cat-demand", methods=["POST"])
@validate_request(CatEvent)  # workaround: validation must go after route for POST due to quart-schema issue
async def cat_demand_event(data: CatEvent):
    try:
        result = await process_cat_event(data.__dict__)
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)