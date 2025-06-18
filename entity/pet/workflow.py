from datetime import datetime
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_pet(entity: dict):
    """
    Workflow orchestration for pet entity.
    """
    await process_set_created_at(entity)
    await process_normalize_type(entity)
    await process_validate_status(entity)

async def process_set_created_at(entity: dict):
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()

async def process_normalize_type(entity: dict):
    if entity.get("type"):
        entity["type"] = entity["type"].lower()

async def process_validate_status(entity: dict):
    allowed_statuses = {"available", "pending", "sold"}
    if "status" in entity and entity["status"] not in allowed_statuses:
        logger.warning(f"Invalid status '{entity['status']}' set to 'available'")
        entity["status"] = "available"