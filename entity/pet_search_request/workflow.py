from typing import Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def process_pet_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    pet_type = entity.get("type")
    status = entity.get("status", "available")

    params = {"status": status}
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch pets in enrichment workflow: {e}")
            logger.exception(e)
            entity["enrichment_success"] = False
            entity["results"] = []
            return entity

    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]

    entity["results"] = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name", ""),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        }
        for p in pets
    ]
    entity["enrichment_success"] = True
    return entity

async def is_enrichment_successful(entity: Dict[str, Any]) -> bool:
    return entity.get("enrichment_success") is True

async def is_enrichment_failed(entity: Dict[str, Any]) -> bool:
    return entity.get("enrichment_success") is False