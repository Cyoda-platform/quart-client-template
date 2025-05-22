from datetime import datetime
from typing import Dict, Any

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only - call business logic functions in sequence
    await process_add_timestamp(entity)
    await process_normalize_status(entity)
    await process_mock_age(entity)
    await process_add_description(entity)
    await process_normalize_id(entity)
    return entity

async def process_add_timestamp(entity: Dict[str, Any]):
    entity['processed_at'] = datetime.utcnow().isoformat() + "Z"

async def process_normalize_status(entity: Dict[str, Any]):
    status = entity.get("status", "").lower()
    entity["is_available"] = (status == "available")

async def process_mock_age(entity: Dict[str, Any]):
    age = entity.get("age")
    if not isinstance(age, int) or age < 0:
        entity["age"] = 3  # default mock age

async def process_add_description(entity: Dict[str, Any]):
    if not entity.get("description"):
        entity["description"] = "Playful pet who loves attention."

async def process_normalize_id(entity: Dict[str, Any]):
    pet_id = entity.get("id")
    if pet_id is not None and not isinstance(pet_id, str):
        entity["id"] = str(pet_id)