from datetime import datetime

async def process_pet(entity: dict) -> dict:
    # Workflow orchestration: call sub-processes in sequence
    await process_fetch_pets(entity)
    await process_store_pets(entity)
    await process_fetch_pet_details(entity)
    await process_store_pet_details(entity)
    await process_mark_favorite(entity)
    return entity

async def process_fetch_pets(entity: dict):
    # Business logic: fetch pets from external API (mocked here)
    # TODO: implement actual fetching logic or call to external service
    entity['pets_fetched_at'] = datetime.utcnow().isoformat() + 'Z'
    entity['pets'] = [{"id": 1, "name": "Fluffy", "category": "cat", "status": "available"}]

async def process_store_pets(entity: dict):
    # Business logic: store fetched pets in entity state
    entity['pets_stored'] = True

async def process_fetch_pet_details(entity: dict):
    # Business logic: fetch details for a specific pet (mocked)
    entity['pet_details_fetched_at'] = datetime.utcnow().isoformat() + 'Z'
    entity['pet_details'] = {"id": 1, "name": "Fluffy", "category": "cat", "status": "available", "photoUrls": [], "tags": []}

async def process_store_pet_details(entity: dict):
    # Business logic: store pet details in entity state
    entity['pet_details_stored'] = True

async def process_mark_favorite(entity: dict):
    # Business logic: mark pet as favorite
    entity['favorite_marked'] = True