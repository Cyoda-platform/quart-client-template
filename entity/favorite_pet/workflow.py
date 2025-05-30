from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_favorite_pet(entity: dict) -> dict:
    # Workflow orchestration only
    await process_add_timestamp(entity)
    await process_add_audit_log(entity)
    return entity

async def process_add_timestamp(entity: dict):
    if "addedAt" not in entity:
        entity["addedAt"] = datetime.utcnow().isoformat() + "Z"

async def process_add_audit_log(entity: dict):
    audit_log = {
        "action": "add_favorite_pet",
        "userId": entity.get("userId"),
        "petId": entity.get("petId"),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        # TODO: replace entity_service and cyoda_auth_service with proper injected services
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="audit_log",
            entity_version=ENTITY_VERSION,
            entity=audit_log,
            workflow=None
        )
    except Exception:
        logger.exception("Failed to add audit_log entity in favorite_pet workflow")