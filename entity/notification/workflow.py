import datetime
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)

async def process_event(entity: dict):
    input_type = entity.get("inputType")
    if input_type == "text":
        await detect_food_request_from_text(entity)
    elif input_type == "audio":
        await detect_food_request_from_audio(entity)
    else:
        entity["detected"] = False
    entity["workflowProcessed"] = True

async def send_notification(entity: dict):
    entity["notification"] = {
        "catId": entity.get("catId"),
        "eventType": "food_request",
        "message": "Emergency! A cat demands snacks",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "queued"
    }
    entity["workflowProcessed"] = True
    logger.info("Notification prepared: %s", entity["notification"])

async def detected_condition(entity: dict) -> bool:
    return entity.get("detected", False)

async def not_detected_condition(entity: dict) -> bool:
    return not entity.get("detected", False)