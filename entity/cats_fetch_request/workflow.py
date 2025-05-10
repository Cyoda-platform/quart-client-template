import logging
import uuid
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cat_cache = {}  # Cache cat info for favorites

async def fetch_cats_from_thecatapi(filters: dict):
    """
    Fetch cat data from TheCatAPI with optional filters.
    """
    params = {}

    if filters:
        if "breed" in filters:
            breed_name = filters["breed"].lower()
            async with httpx.AsyncClient() as client:
                breeds_resp = await client.get("https://api.thecatapi.com/v1/breeds")
                breeds_resp.raise_for_status()
                breeds = breeds_resp.json()
            breed_obj = next((b for b in breeds if b["name"].lower() == breed_name), None)
            if breed_obj:
                params["breed_ids"] = breed_obj["id"]
            else:
                return []

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.thecatapi.com/v1/images/search",
            params={**params, "limit": 10, "has_breeds": True},
            timeout=10,
        )
        resp.raise_for_status()
        images = resp.json()

    cats = []
    for img in images:
        cat_id = img.get("id")
        breed = img.get("breeds")[0] if img.get("breeds") else {}
        cat_info = {
            "id": cat_id,
            "breed": breed.get("name", "Unknown"),
            "age": "Unknown",
            "image_url": img.get("url"),
            "fact": breed.get("description", "No fact available."),
            "location": "Unknown",
        }
        cats.append(cat_info)
        cat_cache[cat_id] = cat_info  # Cache cat info for favorites

    return cats

async def process_update_entity_status_processing(entity: dict):
    entity['status'] = 'processing'
    entity['requestedAt'] = datetime.utcnow().isoformat()

async def process_fetch_cats(entity: dict):
    if entity.get("source") == "cat_api":
        cats = await fetch_cats_from_thecatapi(entity.get("filters", {}))
    else:
        cats = []
    entity['data'] = cats

async def process_update_entity_status_completed(entity: dict):
    entity['status'] = 'completed'
    entity['completedAt'] = datetime.utcnow().isoformat()

async def process_update_entity_status_failed(entity: dict, error: Exception):
    entity['status'] = 'failed'
    entity['error'] = str(error)
    logger.exception(f"Error in processing cats fetch request: {error}")