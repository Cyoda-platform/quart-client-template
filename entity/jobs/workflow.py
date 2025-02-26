import asyncio
import datetime
import aiohttp

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

# Business logic: fetch brands data and update the entity state.
async def process_fetch_brands(entity):
    url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers={"accept": "application/json"}, timeout=10
            ) as resp:
                if resp.status == 200:
                    brands_data = await resp.json()
                    entity["status"] = "completed"
                    entity["brands"] = brands_data
                else:
                    entity["status"] = "error"
    except Exception:
        entity["status"] = "error"

# Business logic: update supplementary brands entity if available.
async def process_update_supplementary_brands(entity):
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="brands",  # this is a different entity_model from the current one.
            entity_version=ENTITY_VERSION,
            entity={"data": entity["brands"]},
            meta={}
        )
    except Exception:
        # Error handling (e.g., logging) can be added here if needed.
        pass

# Business logic: mark the entity with the workflow applied timestamp.
async def process_set_workflow_applied(entity):
    entity["workflow_applied_at"] = datetime.datetime.utcnow().isoformat()

# Workflow orchestration: this function coordinates the workflow steps.
async def process_jobs(entity):
    await process_fetch_brands(entity)
    if entity.get("status") == "completed":
        await process_update_supplementary_brands(entity)
    await process_set_workflow_applied(entity)
    return entity