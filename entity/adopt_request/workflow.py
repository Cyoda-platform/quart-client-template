import asyncio
import logging
from datetime import datetime

adoption_lock = asyncio.Lock()
adoption_status = {}
logger = logging.getLogger(__name__)

async def process_check_availability(entity: dict):
    pet_id = entity.get("petId")
    async with adoption_lock:
        current_status = adoption_status.get(pet_id, "available")
        entity["is_available"] = (current_status == "available")

async def process_mark_adopted(entity: dict):
    pet_id = entity.get("petId")
    user_name = entity.get("userName")
    async with adoption_lock:
        adoption_status[pet_id] = "adopted"
    entity["adoption_success"] = True
    entity["message"] = "Adoption request confirmed."
    entity["adopted_at"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"User '{user_name}' adopted pet {pet_id}")

async def process_adopt_request(entity: dict) -> dict:
    pet_id = entity.get("petId")
    user_name = entity.get("userName")
    if not pet_id or not user_name:
        raise ValueError("petId and userName are required in adopt_request entity")

    await process_check_availability(entity)

    if not entity.get("is_available"):
        entity["adoption_success"] = False
        entity["message"] = "Pet is not available for adoption."
        logger.info(f"Adoption failed: pet {pet_id} already adopted")
    else:
        await process_mark_adopted(entity)

    # Cleanup temporary flags
    entity.pop("is_available", None)

    return entity