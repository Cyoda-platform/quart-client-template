from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_pet_fetch_job(entity: dict):
    # Guard against multiple runs if already completed or failed
    if entity.get("status") in ("completed", "failed"):
        return

    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    try:
        pets = await fetch_pets_from_petstore(
            pet_type=entity.get("type"),
            status=entity.get("status_filter"),
            limit=entity.get("limit")
        )
        stored_ids = []
        for pet in pets:
            pet_data = pet.copy()
            if "id" in pet_data:
                pet_data["id"] = str(pet_data["id"])
            new_id = await process_pet_add(pet_data)
            stored_ids.append(new_id)

        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result_count"] = len(stored_ids)
        entity["stored_ids"] = stored_ids

    except Exception as e:
        logger.exception("Error in pet_fetch_job workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()

async def process_pet_add(entity: dict):
    # TODO: Replace with actual logic to add pet entity, e.g. via entity_service
    # For now, simulate adding by returning pet id string
    return entity.get("id") or "unknown"
