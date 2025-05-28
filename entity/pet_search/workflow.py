from typing import Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)
PETSTORE_BASE = "https://petstore.swagger.io/v2"

async def process_pet_search(entity: Dict[str, Any]) -> None:
    # Workflow orchestration only
    await process_fetch_pets(entity)
    process_filter_pets(entity)
    await process_cache_pets(entity)

async def process_fetch_pets(entity: Dict[str, Any]) -> None:
    status = entity.get("status") or "available"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
            entity["_fetched_pets"] = pets
    except Exception as e:
        logger.warning(f"Pet search external API call failed: {e}")
        entity["_fetched_pets"] = []

def process_filter_pets(entity: Dict[str, Any]) -> None:
    pet_type = entity.get("type")
    tags_filter = set(t.lower() for t in entity.get("tags", []))
    pets = entity.get("_fetched_pets", [])

    def pet_matches(pet):
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            return False
        if tags_filter:
            pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
            if not tags_filter.issubset(pet_tags):
                return False
        return True

    filtered_pets = [
        {
            "id": pet["id"],
            "name": pet.get("name", ""),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "tags": [tag.get("name", "") for tag in pet.get("tags", [])]
        }
        for pet in pets if pet_matches(pet)
    ]
    entity["_filtered_pets"] = filtered_pets
    # Remove temporary fetched pets list to keep entity clean
    entity.pop("_fetched_pets", None)

async def process_cache_pets(entity: Dict[str, Any]) -> None:
    filtered_pets = entity.get("_filtered_pets", [])
    # TODO: If needed, update pet entities in external store here (not current entity)
    # Here we only update the current entity state directly
    entity["pets"] = filtered_pets
    entity.pop("_filtered_pets", None)