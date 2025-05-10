import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

THE_CAT_API_IMAGES_URL = "https://api.thecatapi.com/v1/images/search"

async def process_fetch_image(entity_data: dict):
    breed_id = entity_data.get("id")
    if not breed_id:
        logger.warning("No breed id found in entity_data during workflow processing.")
        entity_data["image_url"] = ""
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {"breed_id": breed_id, "limit": 1}
            resp = await client.get(THE_CAT_API_IMAGES_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list) and "url" in data[0]:
                entity_data["image_url"] = data[0]["url"]
            else:
                entity_data["image_url"] = ""
    except Exception as e:
        logger.warning(f"Failed to fetch image for breed {breed_id} inside workflow: {e}")
        entity_data["image_url"] = ""

def process_add_timestamp(entity_data: dict):
    entity_data["processed_at"] = datetime.utcnow().isoformat()