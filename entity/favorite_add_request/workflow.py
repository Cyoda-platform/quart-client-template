import asyncio
import logging
from datetime import datetime

adoption_status = {}
logger = logging.getLogger(__name__)

async def fetch_pet_by_id(pet_id: str) -> dict:
    pass  # Assume this function is defined elsewhere as in the original code

async def process_favorite_add_request(entity: dict) -> dict:
    # Workflow orchestration only
    await process_validate_pet_id(entity)
    await process_fetch_pet_info(entity)
    process_add_metadata(entity)
    return entity

async def process_validate_pet_id(entity: dict):
    pet_id = entity.get("pet_id")
    if not pet_id:
        raise ValueError("pet_id is required in favorite_add_request entity")

async def process_fetch_pet_info(entity: dict):
    pet_id = entity["pet_id"]
    pet = await fetch_pet_by_id(pet_id)
    if not pet:
        raise ValueError(f"Pet with id {pet_id} not found")
    pet_info = {
        "id": str(pet.get("id")),
        "name": pet.get("name", ""),
        "type": pet.get("category", {}).get("name", "").lower() if pet.get("category") else "",
        "breed": "",  # Petstore does not provide breed info
        "age": 0,     # Petstore does not provide age info
        "status": adoption_status.get(str(pet.get("id")), "available"),
    }
    entity["pet_info"] = pet_info

def process_add_metadata(entity: dict):
    now_iso = datetime.utcnow().isoformat() + "Z"
    entity["added_at"] = now_iso
    entity["processed_at"] = now_iso