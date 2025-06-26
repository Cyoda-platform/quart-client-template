import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def _query_pets(entity: dict) -> list[dict]:
    type_ = entity.get("type")
    status = entity.get("status")
    tags = entity.get("tags")
    params = {}
    if status:
        params["status"] = status
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from external API: {e}")
            return []
    def pet_matches(pet: dict) -> bool:
        if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
            return False
        if tags:
            pet_tags = [t.get("name", "").lower() for t in pet.get("tags", [])]
            if not all(t.lower() in pet_tags for t in tags):
                return False
        return True
    filtered = [p for p in pets if pet_matches(p)]
    return filtered

async def process_petsearchrequest(entity: dict) -> dict:
    # Workflow orchestration only, no business logic here
    pets = await _query_pets(entity)
    entity["pets"] = pets
    return entity