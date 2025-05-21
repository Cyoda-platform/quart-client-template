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

# In-memory async-safe cache/persistence substitutes
# Use asyncio.Lock to simulate concurrency-safe access
pets_cache_lock = asyncio.Lock()
pets_cache: Dict[int, Dict] = {}  # pet_id -> pet data
favorites_lock = asyncio.Lock()
favorites: List[int] = []

# Base Petstore API URL (Swagger Petstore public API)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility: fetch pets from Petstore API by search criteria
async def fetch_pets_from_petstore(
    type_: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
) -> List[Dict]:
    """
    Petstore API does not support complex search by name/type/status via REST GET.
    We will fetch pets by status (available, pending, sold) via /pet/findByStatus as main filter.
    Then filter locally by type & name if provided.
    """
    results = []
    statuses = [status] if status else ["available", "pending", "sold"]
    async with httpx.AsyncClient() as client:
        for st in statuses:
            try:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": st})
                resp.raise_for_status()
                pets = resp.json()
                # Filter by type and name locally
                for pet in pets:
                    if type_ and pet.get("category") and pet["category"].get("name"):
                        if pet["category"]["name"].lower() != type_.lower():
                            continue
                    if name and name.lower() not in pet.get("name", "").lower():
                        continue
                    results.append(pet)
            except Exception as e:
                logger.exception(f"Error fetching pets from Petstore API for status={st}: {e}")
    return results

# Helper: normalize pet data to our API response format
def normalize_pet(pet_raw: Dict) -> Dict:
    return {
        "id": pet_raw.get("id"),
        "name": pet_raw.get("name"),
        "type": pet_raw.get("category", {}).get("name") if pet_raw.get("category") else None,
        "status": pet_raw.get("status"),
        "description": pet_raw.get("description"),
    }

# Background task: cache pet data by ID
async def cache_pets(pets: List[Dict]):
    async with pets_cache_lock:
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id:
                pets_cache[pet_id] = normalize_pet(pet)

# POST /pets/search
@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json()
    type_ = data.get("type")
    status = data.get("status")
    name = data.get("name")

    pets_raw = await fetch_pets_from_petstore(type_, status, name)
    await cache_pets(pets_raw)
    pets_normalized = [normalize_pet(p) for p in pets_raw]
    return jsonify({"pets": pets_normalized})

# GET /pets/{id}
@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if pet:
        return jsonify(pet)
    # If pet not in cache, try to fetch from Petstore API directly
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            resp.raise_for_status()
            pet_raw = resp.json()
            pet = normalize_pet(pet_raw)
            # Cache the fetched pet
            async with pets_cache_lock:
                pets_cache[pet_id] = pet
            return jsonify(pet)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return jsonify({"error": "Pet not found"}), 404
            logger.exception(f"Error fetching pet {pet_id} from Petstore API: {e}")
            return jsonify({"error": "Failed to fetch pet data"}), 500
        except Exception as e:
            logger.exception(f"Unexpected error fetching pet {pet_id}: {e}")
            return jsonify({"error": "Internal server error"}), 500

# POST /pets/add-favorite
@app.route("/pets/add-favorite", methods=["POST"])
async def add_favorite():
    data = await request.get_json()
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400
    # Check if pet exists in cache or Petstore to avoid favorites for unknown pets
    async with pets_cache_lock:
        pet_exists = pet_id in pets_cache
    if not pet_exists:
        # Try to fetch pet from external API to confirm existence
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                resp.raise_for_status()
                pet_raw = resp.json()
                pet = normalize_pet(pet_raw)
                async with pets_cache_lock:
                    pets_cache[pet_id] = pet
                pet_exists = True
            except Exception:
                return jsonify({"error": "Pet not found, cannot add to favorites"}), 404
    async with favorites_lock:
        if pet_id in favorites:
            return jsonify({"success": True, "message": "Pet already in favorites"})
        favorites.append(pet_id)
    return jsonify({"success": True, "message": "Pet added to favorites"})

# GET /favorites
@app.route("/favorites", methods=["GET"])
async def get_favorites():
    async with favorites_lock:
        fav_ids = list(favorites)
    pets_list = []
    async with pets_cache_lock:
        for pet_id in fav_ids:
            pet = pets_cache.get(pet_id)
            if pet:
                pets_list.append(pet)
    return jsonify({"favorites": pets_list})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
