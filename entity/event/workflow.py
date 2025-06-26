import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

async def detect_food_request_from_text(entity: dict) -> None:
    text = entity.get("input_data", "").lower()
    keywords = ["snack", "food", "hungry", "feed", "treat", "meow", "demand"]
    entity["detected"] = any(k in text for k in keywords)

async def detect_food_request_from_audio(entity: dict) -> None:
    # TODO: Implement actual audio detection logic here
    # For now, mock detection as False
    entity["detected"] = False

async def send_notification_entity(cat_id: str, event_type: str, message: str) -> None:
    # TODO: Replace with real notification logic
    logger.info(f"Notification sent for cat {cat_id}: {event_type} - {message}")

async def process_event(entity: dict) -> None:
    entity["processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    input_type = entity.get("input_type")
    cat_id = entity.get("cat_id")

    if not (cat_id and input_type and entity.get("input_data")):
        logger.warning("Event entity missing required fields for processing.")
        return

    try:
        if input_type == "text":
            await detect_food_request_from_text(entity)
        elif input_type == "audio":
            await detect_food_request_from_audio(entity)
        else:
            entity["detected"] = False
    except Exception:
        logger.exception("Failed to detect food request in process_event")
        entity["detected"] = False

    if entity.get("detected"):
        entity["event_type"] = "food_request"
        entity["message"] = "Emergency! A cat demands snacks"
        asyncio.create_task(send_notification_entity(cat_id, entity["event_type"], entity["message"]))
    else:
        entity["event_type"] = None
        entity["message"] = None

async def detected_is_true(entity: dict) -> bool:
    return entity.get("detected") is True

async def detected_is_false(entity: dict) -> bool:
    return entity.get("detected") is not True

async def send_notification_entity(entity: dict) -> None:
    cat_id = entity.get("cat_id")
    event_type = entity.get("event_type")
    message = entity.get("message")
    if cat_id and event_type and message:
        await send_notification_entity(cat_id, event_type, message)
    entity["workflowProcessed"] = True