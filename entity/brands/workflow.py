import asyncio
import datetime
import logging

# Business logic: add processing timestamp to the entity.
def process_add_timestamp(entity):
    entity["workflow_processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# Business logic: ensure entity has a default status.
def process_validate_status(entity):
    if "status" not in entity:
        entity["status"] = "new"
    return entity

# Asynchronous business logic: perform additional async logging.
async def process_async_logging(entity):
    try:
        await asyncio.sleep(0)
        processed_at = entity.get("workflow_processed_at", "unknown time")
        logging.info(f"Async Log: Entity processed at {processed_at}.")
    except Exception as e:
        logging.exception("Error in process_async_logging")

# Workflow orchestration: calls business logic functions.
async def process_brands(entity):
    try:
        process_add_timestamp(entity)
        process_validate_status(entity)
        asyncio.create_task(process_async_logging(entity))
    except Exception as e:
        logging.exception("Error in process_brands")
    return entity