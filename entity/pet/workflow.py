from datetime import datetime
from typing import Dict

async def process_pet(entity: Dict) -> Dict:
    await process_normalize_type(entity)
    await process_set_default_status(entity)
    await process_set_created_at(entity)
    return entity

async def process_normalize_type(entity: Dict):
    pet_type = entity.get("type")
    if pet_type:
        entity["type"] = pet_type.lower()

async def process_set_default_status(entity: Dict):
    if "status" not in entity:
        entity["status"] = "available"

async def process_set_created_at(entity: Dict):
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()