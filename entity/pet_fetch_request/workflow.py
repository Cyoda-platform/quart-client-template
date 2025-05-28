import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

def filter_pets(pets: List[Dict], status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    filtered = pets
    if status:
        filtered = [p for p in filtered if p.get("status") == status]
    if tags:
        filtered = [p for p in filtered if "tags" in p and any(tag in tags for tag in p["tags"])]
    return filtered

def process_petstore_pets(raw_pets: List[Dict]) -> List[Dict]:
    processed = []
    for pet in raw_pets:
        processed.append({
            "id": str(pet.get("id")) if pet.get("id") is not None else None,
            "name": pet.get("name"),
            "status": pet.get("status"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        })
    return processed

async def process_fetch_pets(entity: Dict) -> None:
    status = entity.get("status")
    tags = entity.get("tags")
    logger.info(f"Fetching pets with status={status} tags={tags}")

    async with httpx.AsyncClient() as client:
        api_status = status if status else "available,pending,sold"
        url = f"{PETSTORE_API_BASE}/pet/findByStatus"
        params = {"status": api_status}
        response = await client.get(url, params=params, timeout=10)
        response.raise_for_status()
        raw_pets = response.json()
        filtered_pets = filter_pets(raw_pets, None, tags)
        processed_pets = process_petstore_pets(filtered_pets)
        entity["fetched_pets"] = processed_pets
        logger.info(f"Fetched {len(processed_pets)} pets from external API")

async def process_update_pets(entity: Dict) -> None:
    # TODO: Implement update or persistence logic here if needed
    # For prototype, just mark pets as updated
    pets = entity.get("fetched_pets", [])
    for pet in pets:
        pet["updated_at"] = datetime.utcnow().isoformat()
    entity["pets_updated"] = True
    logger.info("Marked pets as updated")

async def process_finalize(entity: Dict) -> None:
    entity["processed_at"] = datetime.utcnow().isoformat()
    logger.info("Finalized pet fetch request")

async def process_pet_fetch_request(entity: Dict) -> None:
    # Workflow orchestration only
    await process_fetch_pets(entity)
    await process_update_pets(entity)
    await process_finalize(entity)