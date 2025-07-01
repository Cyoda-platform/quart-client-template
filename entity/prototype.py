```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache simulating persistence
# Structure: { user_id: { "favorites": set(petId) } }
user_data_cache: Dict[str, Dict[str, Any]] = {}

# Entity job cache for async processing results (if needed)
entity_jobs: Dict[str, Dict[str, Any]] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

# Helper functions

async def fetch_pets_from_petstore(
    pet_type: str = None, status: str = None
) -> List[Dict[str, Any]]:
    """Fetch pets from the Petstore API applying filters."""
    # Petstore open api for pets: GET /pet/findByStatus or /pet/findByTags
    # Using findByStatus endpoint, type filtering is not direct in Petstore API,
    # so we will filter client-side by 'category.name' (mocked as 'type' here).
    #
    # TODO: Petstore API doesn't provide direct filtering by type, so we fetch by status and filter locally.

    params = {}
    if status:
        # Petstore expects status as csv (available,sold,pending)
        params["status"] = status
    else:
        # Default to 'available' pets if no status
        params["status"] = "available"

    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

    # Filter locally by type (category.name)
    if pet_type:
        filtered = []
        for pet in pets:
            if pet.get("category") and pet["category"].get("name", "").lower() == pet_type.lower():
                filtered.append(pet)
        return filtered
    else:
        return pets

def pet_to_response_obj(pet: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize pet object to response format as per spec."""
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", "") if pet.get("category") else "",
        "status": pet.get("status", ""),
        "photoUrls": pet.get("photoUrls", []),
    }

def get_user_favorites(user_id: str) -> set:
    return user_data_cache.get(user_id, {}).get("favorites", set())

def add_user_favorite(user_id: str, pet_id: int):
    if user_id not in user_data_cache:
        user_data_cache[user_id] = {"favorites": set()}
    user_data_cache[user_id]["favorites"].add(pet_id)

def remove_user_favorite(user_id: str, pet_id: int):
    if user_id in user_data_cache:
        user_data_cache[user_id]["favorites"].discard(pet_id)

async def fetch_pets_by_ids(pet_ids: set) -> List[Dict[str, Any]]:
    """Fetch pet details by IDs from Petstore API (one-by-one)."""
    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        for pet_id in pet_ids:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                if r.status_code == 200:
                    pet = r.json()
                    pets.append(pet)
                # else pet may not exist or deleted - skip silently
            except Exception as e:
                logger.exception(f"Error fetching pet id {pet_id}: {e}")
    return pets

# Routes

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")

    pets = await fetch_pets_from_petstore(pet_type, status)
    pets_response = [pet_to_response_obj(p) for p in pets]

    return jsonify({"pets": pets_response})

@app.route("/favorites/add", methods=["POST"])
async def favorites_add():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"message": "Invalid petId"}), 400

    # TODO: In real app, identify user from auth. Here we use a fixed dummy user.
    user_id = "dummy_user"

    add_user_favorite(user_id, pet_id)
    favorite_count = len(get_user_favorites(user_id))
    return jsonify({"message": "Pet added to favorites", "favoriteCount": favorite_count})

@app.route("/favorites/remove", methods=["POST"])
async def favorites_remove():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"message": "Invalid petId"}), 400

    user_id = "dummy_user"

    remove_user_favorite(user_id, pet_id)
    favorite_count = len(get_user_favorites(user_id))
    return jsonify({"message": "Pet removed from favorites", "favoriteCount": favorite_count})

@app.route("/favorites", methods=["GET"])
async def favorites_get():
    user_id = "dummy_user"
    pet_ids = get_user_favorites(user_id)
    pets = await fetch_pets_by_ids(pet_ids)
    pets_response = [pet_to_response_obj(p) for p in pets]

    return jsonify({"favorites": pets_response})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
