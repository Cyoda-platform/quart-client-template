import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

NOTIFICATION_API_URL = "https://httpbin.org/post"

async def send_notification(entity: dict):
    message = "Emergency! A cat demands snacks"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(NOTIFICATION_API_URL, json={"message": message})
            resp.raise_for_status()
            logger.info(f"Notification sent: {message}")
            entity['notification_sent'] = True
        except Exception as e:
            logger.exception(f"Failed to send notification: {e}")
            entity['notification_sent'] = False

async def evaluate_event(entity: dict):
    event_type = entity.get("event_type")
    intensity = entity.get("intensity")
    timestamp = entity.get("timestamp")
    try:
        event_time = datetime.fromisoformat(timestamp)
    except Exception:
        event_time = datetime.utcnow()
    entity['event_time'] = event_time.isoformat()

    if event_type == "food_request" and intensity == "dramatic":
        await send_notification(entity)
    else:
        entity['notification_sent'] = False
        logger.info(f"No notification needed for event_type={event_type}, intensity={intensity}")

async def condition_is_dramatic_food_request(entity: dict) -> bool:
    return entity.get("event_type") == "food_request" and entity.get("intensity") == "dramatic"

async def condition_is_not_dramatic_food_request(entity: dict) -> bool:
    return not (entity.get("event_type") == "food_request" and entity.get("intensity") == "dramatic")

async def process_product(entity: dict):
    await evaluate_event(entity)