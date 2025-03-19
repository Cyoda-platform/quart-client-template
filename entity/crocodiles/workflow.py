import asyncio
import datetime
import logging

logger = logging.getLogger(__name__)

# Business logic: sets the processed timestamp on the entity.
async def process_set_timestamp(entity: dict):
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# Business logic: performs asynchronous dummy work.
async def process_dummy_work(entity: dict):
    await asyncio.sleep(0)
    return entity

# Workflow orchestration: this function calls only business logic functions.
async def process_crocodiles(entity: dict):
    try:
        await process_set_timestamp(entity)
        await process_dummy_work(entity)
    except Exception as e:
        logger.exception("Error in workflow processing for entity %s: %s", entity, e)
        entity["workflow_error"] = str(e)
    return entity