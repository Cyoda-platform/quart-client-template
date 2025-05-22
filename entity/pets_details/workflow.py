from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_fetch_pet_details(entity: dict):
    pet_id = str(entity.get("petId"))
    logger.info(f"Fetching pet details for pet {pet_id}")
    details = await fetch_pet_details(pet_id)
    entity["details"] = details

async def process_update_status_done(entity: dict):
    entity["status"] = "done"
    entity["completedAt"] = datetime.utcnow().isoformat()

async def process_pets_details(entity: dict) -> dict:
    # Workflow orchestration only
    await process_fetch_pet_details(entity)
    await process_update_status_done(entity)
    return entity