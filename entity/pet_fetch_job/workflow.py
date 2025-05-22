from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def fetch_pets_from_petstore(entity: Dict) -> List[Dict]:
    # Extract filters from entity
    status = entity.get("status_filter")
    pet_type = entity.get("type_filter")
    limit = entity.get("limit_filter", 10)
    # TODO: Implement actual fetch logic here using status, pet_type, limit
    pass

async def process_pet_add(entity: Dict, pet: Dict):
    # Business logic to process and enrich a single pet entity
    # Enrich description or other attributes here
    description = enrich_pet_description(pet)
    pet_entity = {
        "id": str(pet.get("id")),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", "").lower() if "category" in pet else pet.get("type", "").lower(),
        "status": pet.get("status"),
        "description": description,
    }
    # TODO: Add pet_entity to persistent storage via entity_service (outside this function)
    return pet_entity

def enrich_pet_description(pet: Dict) -> str:
    name = pet.get("name", "Unnamed")
    pet_type = pet.get("category", {}).get("name", "pet").lower() if "category" in pet else pet.get("type", "pet").lower()
    status = pet.get("status", "unknown")
    description = f"{name} is a lovely {pet_type} currently {status}."
    if pet_type == "cat":
        description += " Loves naps and chasing yarn balls! 😸"
    elif pet_type == "dog":
        description += " Always ready for a walk and lots of belly rubs! 🐶"
    else:
        description += " A wonderful companion waiting for you!"
    return description

async def process_pet_delete_all(entity: Dict):
    # Delete all existing pets from persistent storage
    try:
        existing_pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.warning(f"Failed to retrieve existing pets for deletion: {e}")
        existing_pets = []
    for existing_pet in existing_pets:
        pet_id = existing_pet.get("id")
        if not pet_id:
            continue
        try:
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
                meta={},
            )
        except Exception as e:
            logger.warning(f"Failed to delete existing pet id {pet_id}: {e}")

async def process_pet_fetch_job(entity: Dict) -> Dict:
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    try:
        pets = await fetch_pets_from_petstore(entity)

        await process_pet_delete_all(entity)

        new_pet_entities = []
        for pet in pets:
            pet_entity = await process_pet_add(entity, pet)
            # TODO: persist pet_entity using entity_service.add_item outside this function
            new_pet_entities.append(pet_entity)

        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["count"] = len(pets)
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.exception("Failed to process pet fetch job")
    return entity