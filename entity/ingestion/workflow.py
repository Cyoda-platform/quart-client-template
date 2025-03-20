import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
PRODUCTS_API_URL = "https://www.automationexercise.com/api/products"

# Business logic: Process the actual ingestion.
async def process_actual_ingestion(entity: dict):
    job_id = entity.get("job_id")
    criteria = entity.get("criteria")
    try:
        logger.info(f"Starting ingestion job {job_id} with criteria: {criteria}")
        async with httpx.AsyncClient() as client:
            response = await client.get(PRODUCTS_API_URL)
            response.raise_for_status()
            data = response.json()
        entity["data"] = data
        entity["ingested_at"] = datetime.utcnow().isoformat()
        entity["status"] = "finished"
        logger.info(f"Ingestion job {job_id} finished successfully.")
    except Exception as e:
        logger.exception(e)
        entity["error"] = str(e)
        entity["ingested_at"] = datetime.utcnow().isoformat()
        entity["status"] = "error"