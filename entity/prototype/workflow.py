import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

async def process_enrich(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("https://httpbin.org/get")
            response.raise_for_status()
            result = response.json()
            entity['enrichment'] = result.get('url', 'unknown')
    except Exception as e:
        logger.warning(f"Failed to enrich prototype entity: {e}")

async def process_delay(entity: dict):
    await asyncio.sleep(0.1)

async def process_prototype(entity: dict) -> dict:
    entity['processedAt'] = datetime.utcnow().isoformat()
    await process_enrich(entity)
    await process_delay(entity)
    return entity