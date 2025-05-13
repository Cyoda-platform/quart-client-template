from datetime import datetime

async def process_pet(entity: dict) -> dict:
    # Workflow orchestration only
    await process_normalize_type(entity)
    await process_add_created_at(entity)
    await process_ensure_tags(entity)
    # Add more process_* calls here if needed
    return entity

async def process_normalize_type(entity: dict):
    if "type" in entity:
        if not entity.get("category") or not isinstance(entity.get("category"), dict):
            entity["category"] = {}
        if isinstance(entity["category"], dict):
            entity["category"]["name"] = entity.pop("type")
        else:
            entity["category"] = {"name": entity.pop("type")}
    else:
        if "category" not in entity or not isinstance(entity.get("category"), dict):
            entity["category"] = {}

async def process_add_created_at(entity: dict):
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat() + "Z"

async def process_ensure_tags(entity: dict):
    if "tags" not in entity or not isinstance(entity.get("tags"), list):
        entity["tags"] = []