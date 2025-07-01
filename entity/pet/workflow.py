from datetime import datetime
import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def normalize_pet(entity: dict):
    if "tags" not in entity or not isinstance(entity["tags"], list):
        entity["tags"] = []
    else:
        entity["tags"] = [str(t) for t in entity["tags"] if isinstance(t, (str, int, float)) and str(t).strip()]
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()
    entity["updatedAt"] = datetime.utcnow().isoformat()
    # Placeholder for adding supplementary entities of different model if needed
    # Uncomment and enable if required and ensure no infinite recursion
    # for tag_name in entity["tags"]:
    #     try:
    #         await entity_service.add_item(
    #             token=cyoda_auth_service,
    #             entity_model="tag",
    #             entity_version=ENTITY_VERSION,
    #             entity={"name": tag_name},
    #             workflow=None
    #         )
    #     except Exception:
    #         logger.exception(f"Failed to add tag entity for tag {tag_name}")
    return entity

async def validate_pet_has_name(entity: dict) -> bool:
    return bool(entity.get("name") and isinstance(entity["name"], str) and entity["name"].strip())

async def not_validate_pet_has_name(entity: dict) -> bool:
    return not await validate_pet_has_name(entity)

async def validate_pet_status(entity: dict) -> bool:
    return entity.get("status") in {"available", "pending", "sold"}

async def not_validate_pet_status(entity: dict) -> bool:
    return not await validate_pet_status(entity)