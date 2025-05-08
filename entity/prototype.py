from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)


@dataclass
class BreedFilter:
    origin: Optional[str] = None
    temperament: Optional[str] = None


@dataclass
class FactsRequest:
    count: int


@dataclass
class ImagesRequest:
    breed_id: Optional[str] = None
    limit: int = 5


@dataclass
class FavoriteRequest:
    user_id: str
    item_type: str  # "breed" | "fact" | "image"
    item_id: str


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
    facts = []
    try:
        async with httpx.AsyncClient() as client:
            limit = min(count, 500)
            r = await client.get(f"{CATFACTS_BASE}/facts?limit={limit}", timeout=10)
            r.raise_for_status()
            data = r.json()
            facts = [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception(e)
    return facts


async def fetch_cat_images(breed_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    params = {"limit": limit}
    if breed_id:
        params["breed_id"] = breed_id

    try:
        async with httpx.AsyncClient() as client:
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
@validate_request(BreedFilter)  # POST validation goes last (after route) - workaround for quart-schema issue
async def post_cats_breeds(data: BreedFilter):
    job_id = "breeds"
    breeds_cache["status"] = "processing"
    breeds_cache["requestedAt"] = datetime.utcnow().isoformat()

    asyncio.create_task(process_breeds_job(job_id, data.__dict__))
    return jsonify({"message": "Breeds data fetching started"}), 202


@app.route("/cats/breeds", methods=["GET"])
@validate_querystring(BreedFilter)  # GET validation goes first (before route) - workaround for quart-schema issue
async def get_cats_breeds():
    breeds = breeds_cache.get("breeds")
    if breeds is None:
        breeds = breeds_cache.get("breeds") or []
    return jsonify({"breeds": breeds})


@app.route("/cats/facts", methods=["POST"])
@validate_request(FactsRequest)
async def post_cats_facts(data: FactsRequest):
    facts_cache.clear()
    facts_cache.append({"status": "processing", "requestedAt": datetime.utcnow().isoformat()})

    asyncio.create_task(process_facts_job("facts", data.count))
    return jsonify({"message": "Cat facts fetching started"}), 202


@app.route("/cats/facts", methods=["GET"])
async def get_cats_facts():
    if not facts_cache or isinstance(facts_cache[0], dict):
        return jsonify({"facts": []})
    return jsonify({"facts": facts_cache})


@app.route("/cats/images", methods=["POST"])
@validate_request(ImagesRequest)
async def post_cats_images(data: ImagesRequest):
    images_cache.clear()
    images_cache.append({"status": "processing", "requestedAt": datetime.utcnow().isoformat()})

    asyncio.create_task(process_images_job("images", data.breed_id, data.limit))
    return jsonify({"message": "Cat images fetching started"}), 202


@app.route("/cats/images", methods=["GET"])
async def get_cats_images():
    if not images_cache or (len(images_cache) == 1 and isinstance(images_cache[0], dict)):
        return jsonify({"images": []})
    return jsonify({"images": images_cache})


@app.route("/favorites", methods=["POST"])
@validate_request(FavoriteRequest)
async def post_favorites(data: FavoriteRequest):
    user_favs = favorites_cache.setdefault(data.user_id, [])

    # TODO: In a full implementation, validate item existence in caches or external APIs.
    user_favs.append({"item_type": data.item_type, "item_id": data.item_id})
    return jsonify({"success": True, "message": "Added to favorites"})


@app.route("/favorites/<string:user_id>", methods=["GET"])
async def get_favorites(user_id):
    user_favs = favorites_cache.get(user_id, [])
    return jsonify({"favorites": user_favs})


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```