import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

CAT_API_BASE_URL = "https://api.thecatapi.com/v1"
CAT_FACTS_API_URL = "https://catfact.ninja/facts"

async def process_set_created_at(entity: dict):
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()

async def process_set_url(entity: dict):
    if not entity.get("url"):
        image_id = entity.get("image_id")
        if image_id:
            entity["url"] = f"https://placekitten.com/400/300?u={image_id}"

async def process_add_metadata(entity: dict):
    image_id = entity.get("image_id")
    if not image_id:
        return
    metadata_entity = {
        "image_id": image_id,
        "source": "user_favorite_upload",
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        # TODO: Replace entity_service and cyoda_auth_service with actual references in implementation
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_image_metadata",
            entity_version=ENTITY_VERSION,
            entity=metadata_entity
        )
    except Exception as e:
        logger.warning(f"Failed to add supplementary cat_image_metadata entity: {e}")