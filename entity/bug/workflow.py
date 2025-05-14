from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def iso8601_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

async def process_set_defaults(entity: dict):
    # Set default status if missing
    if "status" not in entity or not entity["status"]:
        entity["status"] = "open"
    # Normalize and trim string values
    for key in ["title", "description", "reported_by", "steps_to_reproduce"]:
        if key in entity and isinstance(entity[key], str):
            entity[key] = entity[key].strip()

async def process_timestamps(entity: dict):
    now = iso8601_now()
    if "created_at" not in entity:
        entity["created_at"] = now
    entity["updated_at"] = now

async def process_bug(entity: dict) -> dict:
    """
    Workflow function applied to the bug entity asynchronously before persistence.
    Orchestrates processing steps without business logic.
    """
    logger.info(f"Workflow 'process_bug': processing entity before create: {entity.get('title', '<no title>')}")
    await process_set_defaults(entity)
    await process_timestamps(entity)
    return entity