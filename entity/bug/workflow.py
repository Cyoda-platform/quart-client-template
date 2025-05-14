from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def iso8601_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

async def process_normalize_strings(entity: dict):
    for key in ["description", "steps_to_reproduce", "status", "severity"]:
        if key in entity and isinstance(entity[key], str):
            entity[key] = entity[key].strip()

async def process_update_timestamp(entity: dict):
    entity["updated_at"] = iso8601_now()

async def process_bug_update(entity: dict) -> dict:
    """
    Workflow function applied to the bug entity asynchronously before update persistence.
    Orchestrates processing steps without business logic.
    """
    logger.info(f"Workflow 'process_bug_update': processing entity before update: {entity.get('title', '<no title>')}")
    await process_normalize_strings(entity)
    await process_update_timestamp(entity)
    return entity