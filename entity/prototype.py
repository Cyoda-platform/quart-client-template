```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for pets data
# Structure: pet_id -> pet data dict
pets_cache: Dict[int, Dict] = {}

# Simulate async-safe cache access with a lock
pets_cache_lock = asyncio.Lock()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper: convert Petstore pet model to our internal simplified model
def convert_petstore_pet(pet: dict) -> dict:
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "category": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
    }

async def fetch_pets_from_petstore(
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[dict]:
    """
    Fetch pets from Petstore API filtered by status and tags.
    Petstore API supports status filtering on /pet/findByStatus.
    Tags filtering must be done client-side (Petstore doesn't support tag filtering).
    Limit results client-side as well.
    """
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore: {e}")
            return []

    # Filter by tags client-side
    if tags:
        pets = [
            pet for pet in pets
            if pet.get("tags") and any(t.get("name") in tags for t in pet["tags"])
        ]

    # Limit results client-side
    if limit is not None:
        pets = pets[:limit]

    return [convert_petstore_pet(p) for p in pets]

@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Fetch pet data from Petstore API with optional filters and cache them internally.
    """
    data = await request.get_json(force=True, silent=True) or {}

    status = data.get("status")
    tags = data.get("tags")
    limit = data.get("limit")

    # Validate simple types (not strict, as per instructions)
    if tags and not isinstance(tags, list):
        tags = None
    if limit:
        try:
            limit = int(limit)
        except Exception:
            limit = None

    pets = await fetch_pets_from_petstore(status=status, tags=tags, limit=limit)

    # Cache pets internally (overwrite or add)
    async with pets_cache_lock:
        for pet in pets:
            pets_cache[pet["id"]] = pet

    response = {"fetched": len(pets), "pets": pets}
    return jsonify(response)

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Search cached pets by name (substring, case-insensitive) or category.
    Optional filter by status.
    """
    data = await request.get_json(force=True, silent=True) or {}

    query = data.get("query", "").strip().lower()
    status_filter = data.get("status", None)

    async with pets_cache_lock:
        pets_list = list(pets_cache.values())

    def match(pet: dict) -> bool:
        if status_filter and pet.get("status") != status_filter:
            return False
        if query:
            name = pet.get("name", "").lower()
            category = pet.get("category", "").lower() if pet.get("category") else ""
            return query in name or query in category
        return True

    results = [pet for pet in pets_list if match(pet)]

    return jsonify({"results": results})

@app.route("/pets", methods=["GET"])
async def pets_get_all():
    """
    GET /pets
    Return all cached pets.
    """
    async with pets_cache_lock:
        pets_list = list(pets_cache.values())
    return jsonify({"pets": pets_list})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get_by_id(pet_id: int):
    """
    GET /pets/{id}
    Return pet details by ID from cache.
    """
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    return jsonify(pet)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
