from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

async def process_pet_add(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("created_at", datetime.utcnow().isoformat())
    if "tags" in entity and isinstance(entity["tags"], list):
        entity["tags"] = [tag.lower() for tag in entity["tags"]]
    await process_pet_enrich_metadata(entity)
    return entity

async def process_pet_enrich_metadata(entity: Dict[str, Any]) -> None:
    try:
        if "type" in entity and entity["type"]:
            metadata_condition = {
                "type": "simple",
                "jsonPath": "$.pet_type",
                "operatorType": "EQUALS",
                "value": entity["type"].lower()
            }
            pet_metadata = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="pet_metadata",
                entity_version=ENTITY_VERSION,
                condition=metadata_condition
            )
            if pet_metadata:
                entity["metadata"] = pet_metadata[0]
    except Exception:
        logger.exception("Failed to enrich pet metadata in workflow")
