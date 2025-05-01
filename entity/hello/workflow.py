import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def process_fetch_greeting(entity: dict):
    """
    Fetches external greeting asynchronously and sets it on the entity.
    """
    try:
        name = entity.get("name") or "World"
        greeting = await fetch_external_greeting(name)
        entity["greeting"] = greeting
    except Exception as e:
        logger.exception(f"Failed to fetch greeting in process_fetch_greeting: {e}")
        entity["greeting"] = None


async def process_set_requested_at(entity: dict):
    """
    Sets requestedAt on the entity as ISO8601 string if not present or converts datetime.
    """
    if "requestedAt" in entity:
        if isinstance(entity["requestedAt"], datetime):
            entity["requestedAt"] = entity["requestedAt"].isoformat()
    else:
        entity["requestedAt"] = datetime.utcnow().isoformat()


async def process_set_status(entity: dict, status: str):
    """
    Sets the processing status on the entity.
    """
    entity["status"] = status