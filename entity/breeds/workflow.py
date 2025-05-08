import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

THECATAPI_KEY = ""  # Optional but recommended to avoid rate limits
THECATAPI_BASE = "https://api.thecatapi.com/v1"
CATFACTS_BASE = "https://catfact.ninja"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def process_fetch_breeds(entity: Dict[str, Any]) -> List[Dict[str, Any]]:
    filter_data = entity.get("filter", {})
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if THECATAPI_KEY:
                headers["x-api-key"] = THECATAPI_KEY
            r = await client.get(f"{THECATAPI_BASE}/breeds", headers=headers, timeout=10)
            r.raise_for_status()
            breeds = r.json()
    except Exception as e:
        logger.exception(e)
        return []

    origin_filter = filter_data.get("origin")
    temperament_filter = filter_data.get("temperament")

    filtered = []
    for breed in breeds:
        origin = breed.get("origin", "").lower()
        temperament = breed.get("temperament", "").lower()
        if origin_filter and origin_filter.lower() not in origin:
            continue
        if temperament_filter and temperament_filter.lower() not in temperament:
            continue

        filtered.append(
            {
                "id": breed.get("id"),
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "temperament": breed.get("temperament"),
                "description": breed.get("description"),
                "image_url": breed.get("image", {}).get("url"),
            }
        )
    return filtered


async def process_facts(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()

    count = entity.get("count", 5)
    facts = await process_fetch_facts(count)
    entity["facts"] = facts

    entity["status"] = "completed"
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity


async def process_fetch_facts(count: int) -> List[str]:
    try:
        async with httpx.AsyncClient() as client:
            limit = min(count, 500)
            r = await client.get(f"{CATFACTS_BASE}/facts?limit={limit}", timeout=10)
            r.raise_for_status()
            data = r.json()
            facts = [fact["fact"] for fact in data.get("data", [])]
            return facts
    except Exception as e:
        logger.exception(e)
        return []


async def process_images(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()

    breed_id = entity.get("breed_id")
    limit = entity.get("limit", 5)
    images = await process_fetch_images(breed_id, limit)
    entity["images"] = images

    entity["status"] = "completed"
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity


async def process_fetch_images(breed_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    params = {"limit": limit}
    if breed_id:
        params["breed_id"] = breed_id
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if THECATAPI_KEY:
                headers["x-api-key"] = THECATAPI_KEY
            r = await client.get(f"{THECATAPI_BASE}/images/search", headers=headers, params=params, timeout=10)
            r.raise_for_status()
            images = r.json()
            result = []
            for img in images:
                breed_ids = [b.get("id") for b in img.get("breeds", [])] if img.get("breeds") else []
                result.append(
                    {
                        "id": img.get("id"),
                        "url": img.get("url"),
                        "breed_id": breed_ids[0] if breed_ids else None,
                    }
                )
            return result
    except Exception as e:
        logger.exception(e)
        return []


async def process_favorites(entity: Dict[str, Any], favorites_cache: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    # This function assumes favorites_cache is passed externally for modification
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()

    user_id = entity.get("user_id")
    item_type = entity.get("item_type")
    item_id = entity.get("item_id")

    if not (user_id and item_type and item_id):
        entity["status"] = "error"
        entity["message"] = "Missing required fields"
        return entity

    user_favs = favorites_cache.setdefault(user_id, [])
    user_favs.append({"item_type": item_type, "item_id": item_id})

    entity["status"] = "completed"
    entity["message"] = "Added to favorites"
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity