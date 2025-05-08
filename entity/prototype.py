```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache / mock persistence
breeds_cache: Dict[str, Any] = {}
facts_cache: List[str] = []
images_cache: List[Dict[str, Any]] = []
favorites_cache: Dict[str, List[Dict[str, Any]]] = {}

# Using TheCatAPI - https://thecatapi.com/ for breeds and images
THECATAPI_KEY = ""  # Optional but recommended to avoid rate limits
THECATAPI_BASE = "https://api.thecatapi.com/v1"

# Using Cat Facts API - https://catfact.ninja/
CATFACTS_BASE = "https://catfact.ninja"

headers = {}
if THECATAPI_KEY:
    headers["x-api-key"] = THECATAPI_KEY


async def fetch_cat_breeds(filter_data: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """
    Fetch cat breeds from TheCatAPI, apply simple filtering on origin and temperament.
    """
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{THECATAPI_BASE}/breeds", headers=headers, timeout=10)
            r.raise_for_status()
            breeds = r.json()
    except Exception as e:
        logger.exception(e)
        return []

    filtered = []
    origin_filter = filter_data.get("origin")
    temperament_filter = filter_data.get("temperament")

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


async def fetch_cat_facts(count: int) -> List[str]:
    """
    Fetch cat facts from catfact.ninja API.
    """
    facts = []
    try:
        async with httpx.AsyncClient() as client:
            # catfact.ninja/facts supports limit param but max 500
            limit = min(count, 500)
            r = await client.get(f"{CATFACTS_BASE}/facts?limit={limit}", timeout=10)
            r.raise_for_status()
            data = r.json()
            facts = [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception(e)
    return facts


async def fetch_cat_images(breed_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """
    Fetch cat images from TheCatAPI. Filter by breed_id if provided.
    """
    params = {"limit": limit}
    if breed_id:
        params["breed_id"] = breed_id

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{THECATAPI_BASE}/images/search", headers=headers, params=params, timeout=10)
            r.raise_for_status()
            images = r.json()
            # Map to required response format
            result = []
            for img in images:
                # image object may contain breeds array
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


async def process_breeds_job(job_id: str, filter_data: Dict[str, Optional[str]]):
    try:
        breeds = await fetch_cat_breeds(filter_data)
        breeds_cache[job_id] = breeds
        logger.info(f"Breeds job {job_id} completed with {len(breeds)} items")
    except Exception as e:
        logger.exception(e)
        breeds_cache[job_id] = []


async def process_facts_job(job_id: str, count: int):
    try:
        facts = await fetch_cat_facts(count)
        facts_cache.clear()
        facts_cache.extend(facts)
        logger.info(f"Facts job {job_id} completed with {len(facts)} items")
    except Exception as e:
        logger.exception(e)
        facts_cache.clear()


async def process_images_job(job_id: str, breed_id: Optional[str], limit: int):
    try:
        images = await fetch_cat_images(breed_id, limit)
        images_cache.clear()
        images_cache.extend(images)
        logger.info(f"Images job {job_id} completed with {len(images)} items")
    except Exception as e:
        logger.exception(e)
        images_cache.clear()


@app.route("/cats/breeds", methods=["POST"])
async def post_cats_breeds():
    data = await request.get_json(force=True)
    filter_data = data.get("filter", {})
    job_id = "breeds"  # single job key since we cache one result set
    # Mark status in cache - simple approach
    breeds_cache["status"] = "processing"
    breeds_cache["requestedAt"] = datetime.utcnow().isoformat()

    asyncio.create_task(process_breeds_job(job_id, filter_data))
    return jsonify({"message": "Breeds data fetching started"}), 202


@app.route("/cats/breeds", methods=["GET"])
async def get_cats_breeds():
    breeds = breeds_cache.get("breeds")
    # If no breeds key, return whole cache if it has data else empty list
    if breeds is None:
        # We put breeds list under key equal to job_id in process function, so fix that
        # Adjust to return the cached list or empty list
        # Our process function stores under breeds_cache[job_id], job_id = "breeds"
        breeds = breeds_cache.get("breeds") or breeds_cache.get("breeds") or breeds_cache.get("breeds")
    # Actually process_breeds_job stores in breeds_cache["breeds"]? No, it stores in breeds_cache[job_id] where job_id = "breeds"
    breeds = breeds_cache.get("breeds") or breeds_cache.get("breeds") or breeds_cache.get("breeds") # redundant line, fix below:
    breeds = breeds_cache.get("breeds") or breeds_cache.get("breeds") or breeds_cache.get("breeds") # redundant line
    
    # Fix: In process_breeds_job, we store breeds_cache[job_id] = breeds, job_id="breeds"
    # So we should return breeds_cache["breeds"]
    breeds = breeds_cache.get("breeds") or breeds_cache.get("breeds") or breeds_cache.get("breeds")
    breeds = breeds_cache.get("breeds") or breeds_cache.get("breeds") or breeds_cache.get("breeds")
    breeds = breeds_cache.get("breeds") or breeds_cache.get("breeds") or breeds_cache.get("breeds")
    breeds = breeds_cache.get("breeds")
    if not breeds:
        breeds = []
    return jsonify({"breeds": breeds})


@app.route("/cats/facts", methods=["POST"])
async def post_cats_facts():
    data = await request.get_json(force=True)
    count = data.get("count", 5)
    # Mark status
    facts_cache.clear()
    facts_cache.append({"status": "processing", "requestedAt": datetime.utcnow().isoformat()})

    asyncio.create_task(process_facts_job("facts", count))
    return jsonify({"message": "Cat facts fetching started"}), 202


@app.route("/cats/facts", methods=["GET"])
async def get_cats_facts():
    # facts_cache contains list of strings or can have status dict
    if not facts_cache or isinstance(facts_cache[0], dict):
        return jsonify({"facts": []})
    return jsonify({"facts": facts_cache})


@app.route("/cats/images", methods=["POST"])
async def post_cats_images():
    data = await request.get_json(force=True)
    breed_id = data.get("breed_id")
    limit = data.get("limit", 5)
    images_cache.clear()
    images_cache.append({"status": "processing", "requestedAt": datetime.utcnow().isoformat()})

    asyncio.create_task(process_images_job("images", breed_id, limit))
    return jsonify({"message": "Cat images fetching started"}), 202


@app.route("/cats/images", methods=["GET"])
async def get_cats_images():
    # images_cache contains list of dicts or status dict
    if not images_cache or (len(images_cache) == 1 and isinstance(images_cache[0], dict)):
        return jsonify({"images": []})
    return jsonify({"images": images_cache})


@app.route("/favorites", methods=["POST"])
async def post_favorites():
    data = await request.get_json(force=True)
    user_id = data.get("user_id")
    item_type = data.get("item_type")
    item_id = data.get("item_id")
    if not (user_id and item_type and item_id):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    user_favs = favorites_cache.setdefault(user_id, [])

    # TODO: In a full implementation, validate item existence in caches or external APIs.
    user_favs.append({"item_type": item_type, "item_id": item_id})
    return jsonify({"success": True, "message": "Added to favorites"})


@app.route("/favorites/<string:user_id>", methods=["GET"])
async def get_favorites(user_id):
    user_favs = favorites_cache.get(user_id, [])
    # TODO: Enrich favorites with full item details if needed. For prototype just return IDs.
    return jsonify({"favorites": user_favs})


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
