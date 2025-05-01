import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def process_set_status(entity: dict, status: str):
    # Set the processing status on the entity.
    entity["status"] = status


async def process_set_requested_at(entity: dict):
    # Ensure requestedAt is an ISO8601 string.
    if "requestedAt" in entity:
        if isinstance(entity["requestedAt"], datetime):
            entity["requestedAt"] = entity["requestedAt"].isoformat()
    else:
        entity["requestedAt"] = datetime.utcnow().isoformat()


async def process_fetch_greeting(entity: dict):
    # Fetch external greeting asynchronously and set on entity.
    try:
        name = entity.get("name") or "World"
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.quotable.io/random", timeout=5.0)
            r.raise_for_status()
            data = r.json()
            quote = data.get("content", "")
            entity["greeting"] = f"Hello, {name}! Here's a quote for you: \"{quote}\""
    except Exception as e:
        logger.exception(f"Failed to fetch external greeting: {e}")
        entity["greeting"] = f"Hello, {entity.get('name') or 'World'}!"