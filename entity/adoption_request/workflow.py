from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_adoption_request(entity: dict):
    # Orchestrate the workflow steps
    await process_validate_pet(entity)
    await process_set_pending(entity)
    await process_async_approval(entity)
    return entity

async def process_validate_pet(entity: dict):
    pet_id = entity.get("petId")
    # TODO: Replace with real pet validation logic
    # For now, simulate pet validation by setting a flag
    # If pet not found, update entity state and return early
    pet_found = True  # TODO: implement actual pet lookup
    if not pet_found:
        entity["status"] = "failed"
        entity["failureReason"] = "Pet not found"
        logger.warning(f"Adoption request failed: pet {pet_id} not found")

async def process_set_pending(entity: dict):
    entity["status"] = "pending"
    entity["requestedAt"] = datetime.utcnow().isoformat()

async def process_async_approval(entity: dict):
    async def approve():
        try:
            await asyncio.sleep(2)
            entity["status"] = "approved"
            logger.info(f"Adoption {entity.get('adoptionId')} approved for pet {entity.get('petId')}")
        except Exception as e:
            logger.exception(e)
            entity["status"] = "error"
    asyncio.create_task(approve())