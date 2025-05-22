from datetime import datetime
import logging
from app_init.app_init import entity_service
from app_init.app_init import cyoda_auth_service
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_validate_pet_exists(entity: dict):
    pet_id = entity.get("petId")
    if pet_id is None:
        entity["status"] = "failed"
        entity["error"] = "Missing petId"
        logger.error("Adoption request missing petId")
        return
    pet_id_str = str(pet_id)
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id_str,
        )
        if not pet:
            raise ValueError(f"Pet with id {pet_id_str} not found")
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.error(f"Failed validating pet existence: {e}")
        return

async def process_set_submission_status(entity: dict):
    entity["status"] = "submitted"
    entity["submittedAt"] = datetime.utcnow().isoformat()
    user = entity.get("user", {})
    user_name = user.get("name")
    user_email = user.get("email")
    logger.info(f"Adoption request submitted for pet {entity.get('petId')} by {user_name} ({user_email})")

async def process_adoption_request(entity: dict) -> dict:
    # Workflow orchestration only
    await process_validate_pet_exists(entity)
    if entity.get("status") != "failed":
        await process_set_submission_status(entity)
    return entity