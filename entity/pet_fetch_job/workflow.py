import httpx
from datetime import datetime
import logging
from app_init.app_init import entity_service
from app_init.app_init import cyoda_auth_service
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def process_fetch_pets_from_external_api(entity: dict) -> list:
    filters = entity.get("filters") or {}
    async with httpx.AsyncClient(timeout=10) as client:
        statuses = filters.get("status") or "available,pending,sold"
        params = {"status": statuses}
        r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
        r.raise_for_status()
        all_pets = r.json()
    return all_pets


async def process_filter_and_sort_pets(entity: dict, all_pets: list) -> list:
    filters = entity.get("filters") or {}
    limit = entity.get("limit")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        limit = 50
    type_filter = filters.get("type")
    pets = []
    if type_filter:
        type_filter_lower = type_filter.lower()
        for pet in all_pets:
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type == type_filter_lower:
                pets.append(pet)
            if len(pets) >= limit:
                break
    else:
        pets = all_pets[:limit]

    sort_by = entity.get("sortBy")
    if sort_by == "name":
        pets.sort(key=lambda p: p.get("name", "").lower())

    return pets


async def process_upsert_pets(entity: dict, pets: list):
    for pet in pets:
        pet_id_str = str(pet["id"])
        pet_data = {
            "id": pet["id"],
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", "unknown"),
            "status": pet.get("status"),
            "age": None,
            "description": pet.get("description", ""),
            "photos": pet.get("photoUrls", []),
        }
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data,
                technical_id=pet_id_str,
                meta={},
            )
        except Exception:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                    workflow=process_pet,
                )
            except Exception as add_ex:
                logger.error(f"Failed to add pet id {pet_id_str}: {add_ex}")


async def process_pet_fetch_job(entity: dict) -> dict:
    # Workflow orchestration only, no business logic here
    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    try:
        all_pets = await process_fetch_pets_from_external_api(entity)
        pets = await process_filter_and_sort_pets(entity, all_pets)
        await process_upsert_pets(entity, pets)

        entity["status"] = "completed"
        entity["count"] = len(pets)
        entity["completedAt"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception("Error in process_pet_fetch_job")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()

    return entity