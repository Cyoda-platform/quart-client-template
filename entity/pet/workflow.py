import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

favorites_lock = asyncio.Lock()
favorites_cache: Dict[str, dict] = {}

async def process_pet(entity: dict):
    # Workflow orchestration only
    # Example: orchestrate add/update/delete/favorite handling based on entity action
    action = entity.get("action")
    if action == "add":
        await process_add_pet(entity)
    elif action == "update":
        await process_update_pet(entity)
    elif action == "delete":
        await process_delete_pet(entity)
    elif action == "favorite_add":
        await process_favorite_add(entity)
    elif action == "favorite_remove":
        await process_favorite_remove(entity)
    # Set default status and normalize category always
    await process_normalize_pet(entity)

async def process_normalize_pet(entity: dict):
    # Set default status if missing
    if not entity.get("status"):
        entity["status"] = "available"
    # Ensure category is a dict with id and name defaults
    category = entity.get("category")
    if not category or not isinstance(category, dict):
        entity["category"] = {"id": 0, "name": ""}
    else:
        if "name" not in category or category["name"] is None:
            category["name"] = ""
        if "id" not in category or category["id"] is None:
            category["id"] = 0
        entity["category"] = category

async def process_add_pet(entity: dict):
    # Business logic for adding pet, modify entity attributes as needed
    # TODO: Add any additional processing if needed
    pass

async def process_update_pet(entity: dict):
    # Business logic for updating pet, modify entity attributes as needed
    # TODO: Add any additional processing if needed
    pass

async def process_delete_pet(entity: dict):
    # Business logic for deleting pet, modify entity attributes as needed
    # TODO: Add any additional processing if needed
    pass

async def process_favorite_add(entity: dict):
    pet_id = str(entity.get("id"))
    if not pet_id:
        return
    async with favorites_lock:
        favorites_cache[pet_id] = {
            "id": entity.get("id"),
            "name": entity.get("name", ""),
            "type": entity.get("category", {}).get("name", ""),
            "status": entity.get("status", "")
        }

async def process_favorite_remove(entity: dict):
    pet_id = str(entity.get("id"))
    if not pet_id:
        return
    async with favorites_lock:
        if pet_id in favorites_cache:
            del favorites_cache[pet_id]