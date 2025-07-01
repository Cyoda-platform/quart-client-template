from typing import Dict, Any
import logging
from datetime import datetime
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def process_favorite_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    user_id = entity.get("user_id")
    pet_id = entity.get("pet_id")
    action = entity.get("action")

    if not user_id or not pet_id or action not in {"add", "remove"}:
        logger.warning("Invalid favorite_entity data, skipping processing")
        entity["favorite_success"] = False
        return entity

    favorite_entity_model = "favorite_record"
    favorite_entity_id = f"{user_id}_{pet_id}"

    if action == "add":
        try:
            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=favorite_entity_model,
                entity_id=favorite_entity_id,
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.error(f"Failed to get favorite record: {e}")
            existing = None

        if not existing:
            fav_entity = {
                "id": favorite_entity_id,
                "user_id": user_id,
                "pet_id": pet_id,
                "added_at": datetime.utcnow().isoformat() + "Z",
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=favorite_entity_model,
                    entity_version=ENTITY_VERSION,
                    entity=fav_entity,
                    workflow=None,
                )
            except Exception as e:
                logger.error(f"Failed to add favorite record: {e}")
                entity["favorite_success"] = False
                return entity
    elif action == "remove":
        try:
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model=favorite_entity_model,
                entity_id=favorite_entity_id,
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.warning(f"Failed to delete favorite record {favorite_entity_id}: {e}")
            entity["favorite_success"] = False
            return entity

    try:
        favorites_list = await entity_service.search_items(
            token=cyoda_auth_service,
            entity_model=favorite_entity_model,
            entity_version=ENTITY_VERSION,
            filters={"user_id": user_id},
        )
        favorite_count = len(favorites_list)
    except Exception as e:
        logger.error(f"Failed to count favorites for user {user_id}: {e}")
        favorite_count = 0

    entity["favoriteCount"] = favorite_count
    entity["favorite_success"] = True
    return entity

async def is_favorite_successful(entity: Dict[str, Any]) -> bool:
    return entity.get("favorite_success") is True

async def is_favorite_failed(entity: Dict[str, Any]) -> bool:
    return entity.get("favorite_success") is False