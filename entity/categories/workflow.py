import asyncio
import datetime

# Business logic: marks the entity as processed and adds a timestamp
async def process_mark_workflow(entity):
    entity["workflow_processed"] = True
    entity["workflow_timestamp"] = datetime.datetime.utcnow().isoformat()
    return entity

# Business logic: simulates additional asynchronous tasks
async def process_add_sleep(entity):
    await asyncio.sleep(0.1)
    return entity

# Business logic: ensures 'last_refresh' exists in the entity
async def process_set_last_refresh(entity):
    if "last_refresh" not in entity:
        entity["last_refresh"] = datetime.datetime.utcnow().isoformat()
    return entity

# Orchestration: calls the business logic functions in order
async def process_categories(entity):
    try:
        await process_mark_workflow(entity)
        await process_add_sleep(entity)
        await process_set_last_refresh(entity)
    except Exception as e:
        # In production, log the error appropriately
        print(f"Error in workflow processing: {e}")
        raise
    return entity