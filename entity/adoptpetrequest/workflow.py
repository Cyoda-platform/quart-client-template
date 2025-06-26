import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def _fetch_pet_info_from_searches(entity: dict):
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
                    pet_info = {
                        "id": str(pet.get("id")),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name"),
                        "status": pet.get("status")
                    }
                    entity["petInfo"] = pet_info
                    return
    except Exception as e:
        logger.exception("Failed to find pet info from petsearchrequest entities: %s", e)
    entity["petInfo"] = None

async def _fetch_pet_info_from_external_api(entity: dict):
    pet_id = entity.get("petId")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
            pet_info = {
                "id": str(pet.get("id")),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status")
            }
            entity["petInfo"] = pet_info
    except Exception as e:
        logger.warning("Failed to fetch pet info from external API: %s", e)
        entity["petInfo"] = {"id": str(pet_id), "name": None, "type": None, "status": None}

async def _add_adoption(entity: dict):
    pet_info = entity.get("petInfo")
    adopter_name = entity.get("adopterName")
    await cache.add_adoption(adopter_name, pet_info)
    entity["adoptionStatus"] = "confirmed"

async def _finalize_entity(entity: dict):
    entity["workflowProcessed"] = True

async def _pet_info_found_condition(entity: dict) -> bool:
    return entity.get("petInfo") is not None

async def _pet_info_not_found_condition(entity: dict) -> bool:
    return entity.get("petInfo") is None