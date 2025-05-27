import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_pet_fetch(entity: dict) -> dict:
    # Workflow orchestration only - call business logic functions
    await process_fetch_pets(entity)
    return entity

async def process_fetch_pets(entity: dict):
    status = entity.get('status')
    pets = await fetch_pets(status)
    entity['pets'] = pets
    entity['fetched_at'] = datetime.utcnow().isoformat() + 'Z'

async def fetch_pets(status: str = None) -> list:
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
            normalized = []
            for pet in pets:
                normalized.append({
                    "id": str(pet.get("id")),
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name") if pet.get("category") else None,
                    "status": pet.get("status"),
                })
            return normalized
        except Exception:
            logger.exception("Failed to fetch pets from petstore in fetch_pets")
            return []