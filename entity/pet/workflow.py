from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_set_default_description(entity: Dict[str, Any]):
    if not entity.get("description"):
        entity["description"] = "No description provided."

async def process_add_timestamp(entity: Dict[str, Any]):
    entity["processedAt"] = datetime.utcnow().isoformat()

async def process_add_pet_metadata(entity: Dict[str, Any]):
    pet_metadata = {
        "pet_id": entity.get("id"),
        "info": f"Metadata for pet {entity.get('name')}",
        "createdAt": datetime.utcnow().isoformat(),
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_metadata",  # different entity model
            entity_version=ENTITY_VERSION,
            entity=pet_metadata,
            workflow=None,
        )
    except Exception as e:
        logger.warning(f"Failed to add supplementary pet_metadata entity: {e}")

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Orchestrate workflow steps without business logic
    await process_set_default_description(entity)
    await process_add_timestamp(entity)
    await process_add_pet_metadata(entity)
    return entity