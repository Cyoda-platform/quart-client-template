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

# Local in-memory cache for pets added/updated/deleted locally
local_pets: Dict[int, Dict] = {}
local_pet_id_counter = 1

# Cache for last fetched external pets by search parameters (simplified)
external_pets_cache: Dict[str, List[Dict]] = {}

# Petstore API base URL
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

# Lock for local_pets id generation (simple async safe)
local_pets_lock = asyncio.Lock()


def make_cache_key(filters: Dict) -> str:
    # Create a simple cache key based on filters dict sorted by keys
    key = "|".join(f"{k}={v}" for k, v in sorted(filters.items()) if v)
    return key or "all"


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    """
    POST /pets/search
    Accepts optional filters: type, status, name
    Fetches live Petstore API data and returns matching pets.
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")
    name = data.get("name")

    filters = {
        "type": pet_type,
        "status": status,
        "name": name,
    }

    cache_key = make_cache_key(filters)
    if cache_key in external_pets_cache:
        logger.info(f"Returning cached external pets for key: {cache_key}")
        pets = external_pets_cache[cache_key]
        return jsonify({"pets": pets})

    # Build Petstore API URL and query params based on filters
    # Petstore API endpoint: GET /pet/findByStatus or /pet/findByTags or /pet/{petId}
    # The official Petstore API supports filtering by status only for "findByStatus" 
    # No direct filter by type or name, so will filter client-side after fetch.

    pets = []
    async with httpx.AsyncClient() as client:
        try:
            # If status provided, call /pet/findByStatus
            if status:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
            else:
                # If no status, fallback to get all pets by iterating statuses (TODO: Petstore API has no "get all pets" endpoint)
                # TODO: Petstore API does not provide an endpoint to get all pets without status filter.
                # As a placeholder, fetch with status "available"
                r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": "available"})
                r.raise_for_status()
                pets = r.json()

            # Filter by type and name locally (case-insensitive)
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            if name:
                pets = [p for p in pets if name.lower() in p.get("name", "").lower()]
        except Exception as e:
            logger.exception(e)
            return jsonify({"pets": [], "error": "Failed to fetch pets from Petstore API"}), 500

    # Simplify pet data to match our API response model
    simplified_pets = []
    for p in pets:
        simplified_pets.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        })

    # Cache result for this filter key (simple cache, no expiration)
    external_pets_cache[cache_key] = simplified_pets

    return jsonify({"pets": simplified_pets})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    """
    GET /pets/{petId}
    Returns cached or locally stored pet details.
    """
    # Check local pets first
    pet = local_pets.get(pet_id)
    if pet:
        return jsonify(pet)

    # If not local, try to find in the last cached external pets (inefficient but per requirements)
    for pets_list in external_pets_cache.values():
        for p in pets_list:
            if p["id"] == pet_id:
                return jsonify(p)

    return jsonify({"error": "Pet not found"}), 404


@app.route("/pets", methods=["POST"])
async def add_pet():
    """
    POST /pets
    Add a new pet locally.
    """
    data = await request.get_json(force=True)
    name = data.get("name")
    pet_type = data.get("type")
    status = data.get("status")
    photoUrls = data.get("photoUrls", [])

    if not name or not pet_type or not status:
        return jsonify({"error": "Missing required fields: name, type, status"}), 400

    async with local_pets_lock:
        global local_pet_id_counter
        pet_id = local_pet_id_counter
        local_pet_id_counter += 1

        local_pets[pet_id] = {
            "id": pet_id,
            "name": name,
            "type": pet_type,
            "status": status,
            "photoUrls": photoUrls,
        }

    logger.info(f"Added local pet {pet_id}: {name}")
    return jsonify({"id": pet_id, "message": "Pet added successfully"}), 201


@app.route("/pets/<int:pet_id>/update", methods=["POST"])
async def update_pet(pet_id: int):
    """
    POST /pets/{petId}/update
    Update pet locally.
    """
    data = await request.get_json(force=True)
    pet = local_pets.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    # Update fields if provided
    for field in ("name", "type", "status", "photoUrls"):
        if field in data:
            pet[field] = data[field]

    logger.info(f"Updated local pet {pet_id}")
    return jsonify({"message": "Pet updated successfully"})


@app.route("/pets/<int:pet_id>/delete", methods=["POST"])
async def delete_pet(pet_id: int):
    """
    POST /pets/{petId}/delete
    Delete pet locally.
    """
    pet = local_pets.pop(pet_id, None)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    logger.info(f"Deleted local pet {pet_id}")
    return jsonify({"message": "Pet deleted successfully"})


if __name__ == '__main__':
    import sys

    import logging.config

    # Basic logging config for console output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
