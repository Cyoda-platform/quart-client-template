import asyncio
import logging

logger = logging.getLogger(__name__)

_user_favorites_cache = {}

async def process_add_favorite(entity: dict):
    user_id = entity.get("user_id")
    pet_id = entity.get("pet_id")
    if not user_id or not pet_id:
        logger.warning(f"Favorite request missing user_id or pet_id: {entity}")
        entity["status"] = "failed"
        return
    favorites = _user_favorites_cache.setdefault(user_id, set())
    favorites.add(pet_id)
    logger.info(f"Added pet_id={pet_id} to favorites for user_id={user_id}")
    entity["status"] = "completed"

async def process_validate_favorite_request(entity: dict):
    # Example validation step, can extend as needed
    if "user_id" not in entity or "pet_id" not in entity:
        logger.warning(f"Validation failed: missing user_id or pet_id in {entity}")
        entity["status"] = "failed"
    else:
        entity["status"] = "validated"

async def process_favorite_request(entity: dict):
    # Workflow orchestration only, no business logic here
    await process_validate_favorite_request(entity)
    if entity.get("status") == "validated":
        await process_add_favorite(entity)