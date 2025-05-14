from datetime import datetime
from typing import Dict, Any

async def process_search(entity: Dict[str, Any]) -> None:
    # Business logic for search (simulate or call external API)
    # For prototype, just mark as processed and timestamp
    entity["searchProcessed"] = True
    entity["searchProcessedAt"] = datetime.utcnow().isoformat()

async def process_add(entity: Dict[str, Any]) -> None:
    entity["addProcessed"] = True
    entity["addProcessedAt"] = datetime.utcnow().isoformat()

async def process_update(entity: Dict[str, Any]) -> None:
    entity["updateProcessed"] = True
    entity["updateProcessedAt"] = datetime.utcnow().isoformat()

async def process_delete(entity: Dict[str, Any]) -> None:
    entity["deleteProcessed"] = True
    entity["deleteProcessedAt"] = datetime.utcnow().isoformat()

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only, no business logic here
    action = entity.get("action")
    if action == "search":
        await process_search(entity)
    elif action == "add":
        await process_add(entity)
    elif action == "update":
        await process_update(entity)
    elif action == "delete":
        await process_delete(entity)
    entity["processed"] = True
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity