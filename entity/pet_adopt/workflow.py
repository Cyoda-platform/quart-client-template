import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_add_adoption_log(entity: dict):
    pet_id = str(entity.get('petId') or entity.get('pet_id'))
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_adoption_log",
            entity_version=ENTITY_VERSION,
            entity={
                "pet_id": pet_id,
                "action": "adopted",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    except Exception as e:
        logger.warning(f"Failed to add pet_adoption_log entity: {e}")

async def process_pet_adopt(entity: dict) -> dict:
    pet_id = str(entity.get('petId') or entity.get('pet_id'))
    if not pet_id:
        logger.warning("pet_adopt entity missing petId")
        return entity

    if pet_id in adopted_pets_cache:
        entity['adopted'] = True
        entity['message'] = "Pet already adopted"
        logger.info(f"Pet {pet_id} already adopted")
        return entity

    mock_pet = {
        "id": pet_id,
        "name": f"Adopted Pet #{pet_id}",
        "type": "unknown",
        "photoUrls": []
    }
    adopted_pets_cache[pet_id] = mock_pet

    entity['adopted'] = True
    entity['message'] = "Pet successfully adopted!"
    logger.info(f"Pet {pet_id} adopted successfully")

    asyncio.create_task(process_add_adoption_log(entity))

    return entity