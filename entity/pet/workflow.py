import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__) 
logger.setLevel(logging.INFO)

async def process_pet(entity: dict) -> dict:
    # Workflow orchestration only
    entity = await process_timestamps(entity)
    asyncio.create_task(process_enrichment(entity))
    return entity

async def process_timestamps(entity: dict) -> dict:
    # Set or update timestamps
    entity['last_modified'] = datetime.utcnow().isoformat() + 'Z'
    if 'created_at' not in entity:
        entity['created_at'] = datetime.utcnow().isoformat() + 'Z'
    return entity

async def process_enrichment(entity: dict):
    try:
        # Simulate async I/O enrichment
        await asyncio.sleep(0.1)
        entity['enriched'] = True
    except Exception as e:
        logger.error(f"Enrichment task failed: {e}")