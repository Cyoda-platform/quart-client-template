import asyncio
import logging
from datetime import datetime, timedelta

# Constants for egg cooking durations in seconds
EGG_COOK_TIMES = {
    "soft": 240,    # 4 minutes
    "medium": 420,  # 7 minutes
    "hard": 600,    # 10 minutes
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_alarm(entity):
    # Workflow orchestration only
    await process_initialize(entity)
    await process_set_end_time(entity)
    await process_start_timer(entity)
    return entity

async def process_initialize(entity):
    # Normalize status and timestamps
    if "status" not in entity or not entity["status"]:
        entity["status"] = "active"
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()

async def process_set_end_time(entity):
    # Set end_time if missing, based on egg_type
    if "end_time" not in entity or not entity["end_time"]:
        egg_type = entity.get("egg_type")
        if egg_type not in EGG_COOK_TIMES:
            # If invalid egg_type, default to soft
            egg_type = "soft"
            entity["egg_type"] = egg_type
        duration = EGG_COOK_TIMES[egg_type]
        end_time = datetime.utcnow() + timedelta(seconds=duration)
        entity["end_time"] = end_time.isoformat()

async def process_start_timer(entity):
    # Launch the async timer task to update status when alarm ends
    alarm_id = entity.get("id")
    if alarm_id:
        asyncio.create_task(alarm_timer(alarm_id))
    else:
        logger.warning("Alarm entity has no 'id' during workflow; timer not started.")

async def alarm_timer(alarm_id: str):
    # TODO: Implement timer logic or integrate with external scheduler
    pass