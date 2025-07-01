import asyncio
import logging
from datetime import datetime

import httpx
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()['cyoda_auth_service']

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def condition_valid_filter(entity: dict) -> bool:
    filt = entity.get("filter")
    if not isinstance(filt, dict):
        return False
    status = filt.get("status")
    if status is None or not isinstance(status, str):
        return False
    return True

async def action_mark_failed(entity: dict):
    entity["status"] = "failed"
    entity["updatedAt"] = datetime.utcnow().isoformat()

async def condition_fetch_success(entity: dict) -> bool:
    return "fetched_pets" in entity and isinstance(entity["fetched_pets"], list) and len(entity["fetched_pets"]) > 0

async def action_fetch_pets(entity: dict):
    status = None
    category = None
    filt = entity.get("filter")
    if isinstance(filt, dict):
        status = filt.get("status")
        category = filt.get("category")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": status or "available"}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if category:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == category.lower()]
            entity["fetched_pets"] = pets
        except Exception as e:
            logger.exception(e)
            entity["fetched_pets"] = []

async def condition_add_success(entity: dict) -> bool:
    return entity.get("added_count", 0) == len(entity.get("fetched_pets", []))

async def action_add_pets(entity: dict):
    pets = entity.get("fetched_pets", [])
    added_count = 0
    for pet in pets:
        try:
            pet_data = {
                "name": pet.get("name"),
                "category": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "tags": [t.get("name") for t in pet.get("tags", []) if t.get("name")]
            }
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data,
                workflow=None
            )
            added_count += 1
        except Exception as e:
            logger.exception(e)
    entity["added_count"] = added_count

async def action_mark_complete(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()
    entity["updatedAt"] = datetime.utcnow().isoformat()