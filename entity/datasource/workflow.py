import asyncio
import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Business logic functions (each takes a single entity argument)

async def process_set_creation_timestamp(entity):
    # Set a creation timestamp if not already provided.
    if "created_at" not in entity:
        entity["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

async def process_set_unique_identifier(entity):
    # Set a unique identifier if not already provided.
    if "id" not in entity:
        entity["id"] = str(uuid.uuid4())
    return entity

async def process_log_entity(entity):
    try:
        await asyncio.sleep(0.1)  # Simulate delay for logging
        logger.info("Entity created with id: %s at %s", entity.get("id"), entity.get("created_at"))
    except Exception as log_exc:
        logger.exception("Error in asynchronous logging: %s", log_exc)
    return entity