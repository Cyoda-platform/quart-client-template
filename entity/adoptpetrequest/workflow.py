import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def _fetch_pet_info_from_searches(entity: dict) -> dict | None:
    pet_id = entity.get("petId")
    try:
        all_searches = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
        )
        for search in all_searches:
            pets = search.get("pets")
            if pets is None:
                pets = await query_pets(search.get("type"), search.get("status"), search.get("tags"))
            for pet in pets:
                if str(pet.get("id")) == str(pet_id):
                    return {
                        "id": str(pet.get("id")),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name"),
                        "status": pet.get("status")
                    }
    except Exception as e:
        logger.exception("Failed to find pet info from petsearchrequest entities: %s", e)
    return None

async def _fetch_pet_info_from_external_api(entity: dict) -> dict:
    pet_id = entity.get("petId")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
            return {
                "id": str(pet.get("id")),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status")
            }
    except Exception as e:
        logger.warning("Failed to fetch pet info from external API: %s", e)
        return {"id": str(pet_id), "name": None, "type": None, "status": None}

async def _add_adoption(entity: dict, pet_info: dict):
    adopter_name = entity.get("adopterName")
    await cache.add_adoption(adopter_name, pet_info)

async def process_adoptpetrequest(entity: dict) -> dict:
    # workflow orchestration only - no business logic here
    pet_info = await _fetch_pet_info_from_searches(entity)
    if pet_info is None:
        pet_info = await _fetch_pet_info_from_external_api(entity)
    await _add_adoption(entity, pet_info)
    entity["adoptionStatus"] = "confirmed"
    entity["petInfo"] = pet_info
    return entity