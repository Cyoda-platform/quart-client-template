import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

async def process_timestamp(entity: dict) -> dict:
    # Add a processed_at timestamp to the entity.
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity

async def process_supplementary(entity: dict) -> dict:
    # Fetch supplementary data asynchronously and update the entity.
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://example.com/api/supplementary")
            response.raise_for_status()
            supplementary_data = response.json()
        entity["supplementary"] = supplementary_data
    except Exception as e:
        logger.exception("Error in process_supplementary: %s", e)
        entity["supplementary"] = {}
    return entity