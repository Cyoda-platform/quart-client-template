from typing import Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def process_favorite(entity: Dict) -> Dict:
    # Workflow orchestration only
    await process_enrich_pet_data(entity)
    process_mark_added(entity)
    return entity

async def process_enrich_pet_data(entity: Dict):
    pet_id = entity.get("id") or entity.get("petId")
    if not pet_id:
        logger.warning("No petId found in favorite entity for enrichment.")
        return

    pet_data = await fetch_pet_by_id(int(pet_id))
    if pet_data:
        entity["id"] = pet_data.get("id")
        entity["name"] = pet_data.get("name")
        entity["type"] = pet_data.get("category", {}).get("name")
        entity["status"] = pet_data.get("status")
        entity["tags"] = [tag.get("name") for tag in pet_data.get("tags", [])]
        entity["photoUrls"] = pet_data.get("photoUrls", [])
    else:
        logger.warning(f"Pet data not found for petId {pet_id}, favorite entity unchanged.")

def process_mark_added(entity: Dict):
    entity["added_at"] = datetime.utcnow().isoformat() + "Z"