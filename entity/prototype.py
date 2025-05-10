from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation

@dataclass
class FetchFilters:
    breed: Optional[str] = None
    age: Optional[str] = None
    location: Optional[str] = None

@dataclass
class CatsFetchRequest:
    source: str
    filters: Optional[Dict[str, Any]] = None  # Dynamic, no strict validation on filters content

@dataclass
class FavoriteRequest:
    user_id: str
    cat_id: str

# In-memory stores for prototype
entity_job = {}  # Stores fetch jobs: job_id -> {status, requestedAt, data}
user_favorites = {}  # Stores user favorites: user_id -> set(cat_id)
cat_cache = {}  # Cache cat info by cat_id for favorites display

# External real API for cat data (TheCatAPI)
THE_CAT_API_KEY = ""  # TODO: Optional, get your free API key at https://thecatapi.com/
THE_CAT_API_BASE = "https://api.thecatapi.com/v1"


async def fetch_cats_from_thecatapi(filters: dict):
    """
    Fetch cat data from TheCatAPI with optional filters.
    """
    params = {}

    # Map filters to TheCatAPI params
    if filters:
        if "breed" in filters:
            # Breed filtering requires first fetching breed IDs
            breed_name = filters["breed"].lower()
            async with httpx.AsyncClient() as client:
                breeds_resp = await client.get(f"{THE_CAT_API_BASE}/breeds")
                breeds_resp.raise_for_status()
                breeds = breeds_resp.json()
            breed_obj = next((b for b in breeds if b["name"].lower() == breed_name), None)
            if breed_obj:
                params["breed_ids"] = breed_obj["id"]
            else:
                # No such breed found, return empty
                return []
        # TODO: TheCatAPI does not support age or location filtering.
        # These filters will be ignored or could be implemented with other APIs.

    # Fetch images of cats with applied filters
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{THE_CAT_API_BASE}/images/search",
            params={**params, "limit": 10, "has_breeds": True},
            headers={"x-api-key": THE_CAT_API_KEY} if THE_CAT_API_KEY else {},
            timeout=10,
        )
        resp.raise_for_status()
        images = resp.json()

    cats = []
    for img in images:
        cat_id = img.get("id")
        breed = img.get("breeds")[0] if img.get("breeds") else {}
        cats.append(
            {
                "id": cat_id,
                "breed": breed.get("name", "Unknown"),
                "age": "Unknown",  # TODO: No age info from TheCatAPI
                "image_url": img.get("url"),
                "fact": breed.get("description", "No fact available."),
                "location": "Unknown",  # TODO: No location info from TheCatAPI
            }
        )
        cat_cache[cat_id] = cats[-1]  # Cache for favorites lookup

    return cats


async def process_entity(job_store: dict, job_id: str, data: dict):
    """
    Process the fetch job asynchronously.
    """
    try:
        logger.info(f"Processing fetch job {job_id} with data: {data}")
        # For now, only support source "cat_api"
        if data.get("source") == "cat_api":
            cats = await fetch_cats_from_thecatapi(data.get("filters", {}))
        else:
            # Unsupported source - return empty list
            # TODO: Implement other sources if needed
            cats = []

        job_store[job_id]["status"] = "completed"
        job_store[job_id]["data"] = cats
        job_store[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Fetch job {job_id} completed with {len(cats)} cats")
    except Exception as e:
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
        logger.exception(e)


@app.route("/cats/fetch", methods=["POST"])
@validate_request(CatsFetchRequest)  # Validation last in POST due to Quart-Schema issue workaround
async def cats_fetch(data: CatsFetchRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task
    asyncio.create_task(process_entity(entity_job, job_id, data.__dict__))

    return jsonify({"request_id": job_id, "status": "processing"}), 202


@app.route("/cats/results/<request_id>", methods=["GET"])
async def cats_results(request_id):
    # GET request without validation, fetching by path param only
    job = entity_job.get(request_id)
    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    response = {
        "request_id": request_id,
        "status": job.get("status", "processing"),
        "data": job.get("data", []),
    }
    if job.get("status") == "failed":
        response["error"] = job.get("error", "Unknown error")

    return jsonify(response), 200


@app.route("/cats/favorites", methods=["POST"])
@validate_request(FavoriteRequest)  # Validation last in POST due to Quart-Schema issue workaround
async def add_favorite(data: FavoriteRequest):
    user_id = data.user_id
    cat_id = data.cat_id
    if not user_id or not cat_id:
        return jsonify({"success": False, "message": "user_id and cat_id are required"}), 400

    if user_id not in user_favorites:
        user_favorites[user_id] = set()
    user_favorites[user_id].add(cat_id)

    # Cache cat info if not present - TODO: Incomplete if cat_id unknown, could fetch from TheCatAPI or skip
    if cat_id not in cat_cache:
        cat_cache[cat_id] = {
            "id": cat_id,
            "breed": "Unknown",
            "image_url": None,
        }

    return jsonify({"success": True, "message": "Cat added to favorites"}), 200


@app.route("/cats/favorites/<user_id>", methods=["GET"])
async def get_favorites(user_id):
    # GET request without validation, fetching by path param only
    favs = user_favorites.get(user_id, set())
    favorites_list = []
    for cat_id in favs:
        cat = cat_cache.get(cat_id)
        if cat:
            favorites_list.append(
                {
                    "cat_id": cat_id,
                    "breed": cat.get("breed", "Unknown"),
                    "image_url": cat.get("image_url"),
                }
            )
        else:
            # If cat info is missing, return minimal info
            favorites_list.append({"cat_id": cat_id, "breed": "Unknown", "image_url": None})

    return jsonify({"user_id": user_id, "favorites": favorites_list}), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```