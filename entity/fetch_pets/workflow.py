import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

async def process_fetch_pets(entity: Dict[str, Any]) -> None:
    # Orchestrate workflow steps without business logic
    await process_retrieve_pets(entity)
    await process_add_pet_entities(entity)
    process_set_fetched_at(entity)

async def process_retrieve_pets(entity: Dict[str, Any]) -> None:
    category = entity.get("category")
    status = entity.get("status")
    pets = await fetch_pets_from_petstore(category, status)
    entity["retrieved_pets"] = pets

async def process_add_pet_entities(entity: Dict[str, Any]) -> None:
    pets = entity.get("retrieved_pets", [])
    for pet in pets:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet,
                workflow=process_pet
            )
        except Exception as e:
            logger.exception(f"Error adding pet entity: {e}")

def process_set_fetched_at(entity: Dict[str, Any]) -> None:
    entity["fetched_at"] = datetime.utcnow().isoformat() + "Z"