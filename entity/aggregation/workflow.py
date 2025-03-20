import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
PRODUCTS_API_URL = "https://www.automationexercise.com/api/products"

# Business logic: mark the entity as processed.
async def process_mark_as_processed(entity: dict):
    entity["workflow_processed"] = True
    return entity

# Business logic: fetch products data.
async def process_fetch_products(entity: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(PRODUCTS_API_URL)
            response.raise_for_status()
            data = response.json()
        entity["products_data"] = data
    except Exception as e:
        logger.exception(e)
        entity["products_error"] = str(e)
    return entity

# Business logic: compute aggregation metrics.
async def process_compute_metrics(entity: dict):
    entity["aggregated_at"] = datetime.utcnow().isoformat()
    return entity