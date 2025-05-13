import datetime

async def process_normalize_status(entity: dict):
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()

async def process_normalize_category(entity: dict):
    if "category" in entity and isinstance(entity["category"], dict):
        name = entity["category"].get("name")
        if name and isinstance(name, str):
            entity["category"]["name"] = name.lower()

async def process_add_created_at(entity: dict):
    if "created_at" not in entity:
        entity["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"

async def process_pet(entity: dict) -> dict:
    # Orchestrate workflow steps without business logic
    await process_normalize_status(entity)
    await process_normalize_category(entity)
    await process_add_created_at(entity)
    # Placeholder for additional workflow steps if needed
    return entity