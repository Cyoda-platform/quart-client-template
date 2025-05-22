from datetime import datetime
import logging

logger = logging.getLogger(__name__)
PET_ENTITY_NAME = "pet"
ENTITY_VERSION = ENTITY_VERSION
entity_service = entity_service
cyoda_auth_service = cyoda_auth_service

async def process_fetch_pets(entity: dict):
    filters = {
        "status": entity.get("status"),
        "type": entity.get("type"),
        "name": entity.get("name"),
    }
    pets = await fetch_pets(filters)
    return pets

async def process_update_pet_entities(entity: dict, pets: list):
    for pet in pets:
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=pet,
                technical_id=str(pet["id"]),
                meta={},
            )
        except Exception as e:
            logger.exception(f"Failed updating pet {pet['id']} in entity_service: {e}")

async def process_pets_search_job(entity: dict) -> dict:
    logger.info(f"Processing search job {entity.get('searchId')} in workflow")

    pets = await process_fetch_pets(entity)
    await process_update_pet_entities(entity, pets)

    entity["status"] = "done"
    entity["pets"] = pets
    entity["completedAt"] = datetime.utcnow().isoformat()

    return entity