```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches for last query results and pet details
# Using asyncio.Lock to avoid race conditions
class Cache:
    def __init__(self):
        self._pets_list = None
        self._pets_list_lock = asyncio.Lock()

        self._pets_details: Dict[int, Dict[str, Any]] = {}
        self._pets_details_lock = asyncio.Lock()

cache = Cache()

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

# Helper: fetch pets list from external Petstore API based on filters
async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    # Petstore API supports GET /pet/findByStatus?status={status}
    # and GET /pet/findByTags?tags={tags} but not category filtering directly
    # We will combine queries by status and tags if provided
    # TODO: Petstore API does not support category filtering directly; filter client side
    
    pets = []
    try:
        async with httpx.AsyncClient() as client:
            # Fetch by status
            status = filters.get("status")
            tags = filters.get("tags")
            category = filters.get("category")

            pets_by_status = []
            if status:
                resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
                resp.raise_for_status()
                pets_by_status = resp.json()
            else:
                # If no status filter, fallback to find all available pets by status 'available' (per Petstore API)
                resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": "available"})
                resp.raise_for_status()
                pets_by_status = resp.json()

            # Filter by tags client side (tags are array of objects with 'name' field)
            if tags:
                tags_set = set(tags)
                pets_by_status = [
                    p for p in pets_by_status
                    if "tags" in p and any(t.get("name") in tags_set for t in p["tags"])
                ]

            # Filter by category client side (category is object with 'name')
            if category:
                pets_by_status = [
                    p for p in pets_by_status
                    if "category" in p and p["category"] and p["category"].get("name") == category
                ]

            pets = pets_by_status

    except Exception as e:
        logger.exception(e)
        # Return empty list on error for UX continuity
        pets = []

    return {"pets": pets}


# Helper: fetch pet detail by pet id from Petstore API
async def fetch_pet_detail_from_petstore(pet_id: int) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
            return pet
    except Exception as e:
        logger.exception(e)
        return {}


# Background task to fetch pets list and cache it
async def process_pets_query(filters: Dict[str, Any]):
    pets_data = await fetch_pets_from_petstore(filters)
    async with cache._pets_list_lock:
        cache._pets_list = pets_data


# Background task to fetch pet detail and cache it
async def process_pet_detail(pet_id: int):
    pet_detail = await fetch_pet_detail_from_petstore(pet_id)
    async with cache._pets_details_lock:
        cache._pets_details[pet_id] = pet_detail


@app.route("/pets/query", methods=["POST"])
async def pets_query():
    data = await request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Start background task to fetch pets and cache result
    await asyncio.create_task(process_pets_query(data))

    # Return accepted response immediately (UX: user will call GET /pets to get results)
    return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat()}), 202


@app.route("/pets", methods=["GET"])
async def get_pets():
    async with cache._pets_list_lock:
        if cache._pets_list is None:
            return jsonify({"error": "No pets data cached yet. Please POST /pets/query first."}), 404
        return jsonify(cache._pets_list)


@app.route("/pets/details", methods=["POST"])
async def pet_details_post():
    data = await request.get_json(force=True, silent=True)
    if data is None or "id" not in data:
        return jsonify({"error": "Missing 'id' in request body"}), 400

    pet_id = data["id"]
    if not isinstance(pet_id, int):
        return jsonify({"error": "'id' must be an integer"}), 400

    # Start background task to fetch pet detail and cache it
    await asyncio.create_task(process_pet_detail(pet_id))

    return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "petId": pet_id}), 202


@app.route("/pets/details/<int:pet_id>", methods=["GET"])
async def pet_details_get(pet_id: int):
    async with cache._pets_details_lock:
        pet_detail = cache._pets_details.get(pet_id)
        if pet_detail is None:
            return jsonify({"error": f"No cached details for pet ID {pet_id}. Please POST /pets/details first."}), 404
        return jsonify(pet_detail)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```