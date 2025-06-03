from datetime import datetime
from typing import Dict, Any

async def process_pet_search(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Here should be business logic for searching pets, e.g. filtering external data
    # For prototype: simulate setting a "search_results" attribute
    entity['search_results'] = []  # TODO: populate with actual search results
    entity['search_completed_at'] = datetime.utcnow().isoformat()
    return entity

async def process_pet_add(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Business logic for adding a pet
    entity['created_at'] = datetime.utcnow().isoformat()
    entity['status'] = entity.get('status', 'available').lower() if isinstance(entity.get('status'), str) else 'available'
    # Additional processing or enrichment can be placed here
    return entity

async def process_pet_update(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["updated_at"] = datetime.utcnow().isoformat()
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    # Workflow orchestration: call other process_* functions as needed (example)
    # No direct business logic here, only orchestration
    # Example:
    # if entity.get('action') == 'add':
    #     await process_pet_add(entity)
    # elif entity.get('action') == 'search':
    #     await process_pet_search(entity)
    # else:
    #     # default update logic or enrichment
    #     pass
    return entity

async def process_pet_delete(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Business logic for deleting a pet
    entity['deleted_at'] = datetime.utcnow().isoformat()
    entity['status'] = 'deleted'
    return entity