import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STATE_IDLE = "idle"
STATE_PROCESSING = "processing"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"


async def fetch_external_greeting() -> str:
    """
    Fetch greeting message from an external API.
    Using https://api.github.com/zen as a placeholder for an external API returning a string.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/zen")
            response.raise_for_status()
            return response.text.strip()
    except Exception as e:
        logger.exception("Failed to fetch external greeting: %s", e)
        return "Hello World!"


async def process_prepare(entity: dict):
    entity["status"] = STATE_PROCESSING
    entity["startedAt"] = datetime.utcnow().isoformat()


async def process_fetch_greeting(entity: dict):
    entity["external_greeting"] = await fetch_external_greeting()


async def process_compose_output(entity: dict):
    user_msg = entity.get("event_data", {}).get("message") or entity.get("external_greeting")
    entity["output"] = f"{user_msg}"


async def process_finalize(entity: dict):
    entity["status"] = STATE_COMPLETED
    entity["completedAt"] = datetime.utcnow().isoformat()
    # Clean up temporary keys
    if "external_greeting" in entity:
        del entity["external_greeting"]


async def process_handle_failure(entity: dict, exc: Exception):
    logger.exception("Workflow processing failed: %s", exc)
    entity["status"] = STATE_FAILED
    entity["error"] = str(exc)