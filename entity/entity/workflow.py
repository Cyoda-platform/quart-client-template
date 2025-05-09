import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def process_initialize(entity: dict) -> None:
    """
    Initialize entity state before fetching.
    """
    entity.setdefault("fetch_status", "pending")
    if "fetched_data" not in entity:
        entity["fetched_data"] = None
    if "fetched_at" not in entity:
        entity["fetched_at"] = None

async def process_fetch_data(entity: dict) -> None:
    """
    Fetch data from external API and update entity fields.
    """
    api_url = entity.get("api_url")
    if not api_url:
        entity["fetch_status"] = "error: missing api_url"
        entity["fetched_data"] = None
        entity["fetched_at"] = None
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        entity["fetched_data"] = data
        entity["fetched_at"] = utc_now_iso()
        entity["fetch_status"] = "success"
    except Exception as e:
        logger.exception(f"Error fetching external API for entity inside workflow: {e}")
        entity["fetched_data"] = None
        entity["fetched_at"] = None
        entity["fetch_status"] = f"error: {str(e)}"
