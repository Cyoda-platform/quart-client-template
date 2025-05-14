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

# Local in-memory caches (per app instance, async safe usage via asyncio.Lock)
pets_cache: Dict[int, dict] = {}
favorites_cache: Dict[int, dict] = {}
pets_cache_lock = asyncio.Lock()
favorites_cache_lock = asyncio.Lock()

# Petstore API base URL (public Petstore API)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper async function to call Petstore API (GET)
async def petstore_get(endpoint: str, params: Optional[dict] = None) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}{endpoint}", params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Petstore GET error on {endpoint}: {e}")
            return {}

# Helper async function to call Petstore API (POST/PUT)
async def petstore_post(endpoint: str, json_data: dict, method: str = "POST") -> dict:
    async with httpx.AsyncClient() as client:
        try:
            if method == "POST":
                resp = await client.post(f"{PETSTORE_BASE_URL}{endpoint}", json=json_data, timeout=10)
            else:
                resp = await client.put(f"{PETSTORE_BASE_URL}{endpoint}", json=json_data, timeout=10)
            resp.raise_for_status()
            # Petstore returns empty body on some operations, so fallback to status code
            if resp.content:
                return resp.json()
            else:
                return {"status": resp.status_code}
        except Exception as e:
            logger.exception(f"Petstore {method} error on {endpoint}: {e}")
            return {}

# Utility to add a fun description to a pet
def add_fun_description(pet: dict) -> dict:
    pet = pet.copy()
    pet_type = pet.get("category", {}).get("name", pet.get("type", "pet"))
    pet["description"] = f"A wonderful {pet_type} named {pet.get('name', 'Unknown')} ready to find a home!"
    return pet

# Endpoint: POST /pets/search - fetch pets from Petstore API and filter locally (if needed)
@app.route("/pets/search", methods=["POST"])
async def search_pets():
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")

    # Petstore API does not support direct filtering by type/status on /pet/findByStatus or /pet/findByTags,
    # so we use findByStatus if status is provided, else get all (TODO: Petstore limitation)
    pets_raw: List[dict] = []
    try:
        if status:
            pets_raw = await petstore_get("/pet/findByStatus", params={"status": status})
        else:
            # TODO: Petstore API does not have endpoint to fetch all pets without status
            # Use "available" as default status filter for demonstration
            pets_raw = await petstore_get("/pet/findByStatus", params={"status": "available"})
    except Exception as e:
        logger.exception("Error fetching pets from Petstore API")

    # Filter by type if specified
    filtered_pets = []
    for pet in pets_raw:
        # Petstore uses category.name or tags to specify type, fallback to pet['type']
        pet_type_name = pet.get("category", {}).get("name", None)
        if pet_type:
            if pet_type_name and pet_type_name.lower() != pet_type.lower():
                continue
        filtered_pets.append(add_fun_description(pet))

    # Cache pets locally for retrieval by id
    async with pets_cache_lock:
        for pet in filtered_pets:
            pets_cache[pet["id"]] = pet

    return jsonify({"pets": filtered_pets})

# Endpoint: POST /pets/add - create pet in Petstore API
@app.route("/pets/add", methods=["POST"])
async def add_pet():
    data = await request.get_json(force=True)
    name = data.get("name")
    pet_type = data.get("type")
    status = data.get("status")

    # Petstore expects a full pet object; minimal required fields are id, category, name, photoUrls, tags, status
    # We'll generate a random id (TODO: better id generation or fetch from Petstore)
    import random
    pet_id = random.randint(100000, 999999)

    pet_payload = {
        "id": pet_id,
        "category": {"id": 0, "name": pet_type or "unknown"},
        "name": name or "Unnamed",
        "photoUrls": [],
        "tags": [],
        "status": status or "available",
    }

    resp = await petstore_post("/pet", pet_payload, method="POST")
    if resp.get("status") in [200, 201] or resp == {}:
        # Cache locally
        pet_with_desc = add_fun_description(pet_payload)
        async with pets_cache_lock:
            pets_cache[pet_id] = pet_with_desc
        return jsonify({"success": True, "petId": pet_id})

    return jsonify({"success": False}), 500

# Endpoint: GET /pets/{petId} - get pet details from local cache or fallback to Petstore API
@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if pet:
        return jsonify(pet)

    # Fallback: get from Petstore API
    pet_raw = await petstore_get(f"/pet/{pet_id}")
    if pet_raw and pet_raw.get("id") == pet_id:
        pet_with_desc = add_fun_description(pet_raw)
        async with pets_cache_lock:
            pets_cache[pet_id] = pet_with_desc
        return jsonify(pet_with_desc)

    return jsonify({"error": "Pet not found"}), 404

# Endpoint: POST /pets/update/{petId} - update pet using Petstore API
@app.route("/pets/update/<int:pet_id>", methods=["POST"])
async def update_pet(pet_id: int):
    data = await request.get_json(force=True)
    # Get current cached pet or fetch from Petstore
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)

    if not pet:
        pet = await petstore_get(f"/pet/{pet_id}")
        if not pet or pet.get("id") != pet_id:
            return jsonify({"success": False, "error": "Pet not found"}), 404

    # Update fields if provided
    pet["name"] = data.get("name", pet.get("name"))
    pet["category"] = {"id": 0, "name": data.get("type", pet.get("category", {}).get("name", "unknown"))}
    pet["status"] = data.get("status", pet.get("status"))

    # Prepare payload for Petstore update (PUT)
    pet_payload = {
        "id": pet_id,
        "category": pet["category"],
        "name": pet["name"],
        "photoUrls": pet.get("photoUrls", []),
        "tags": pet.get("tags", []),
        "status": pet["status"],
    }

    resp = await petstore_post("/pet", pet_payload, method="PUT")
    if resp.get("status") in [200, 201] or resp == {}:
        # Update local cache with fun description
        pet_with_desc = add_fun_description(pet_payload)
        async with pets_cache_lock:
            pets_cache[pet_id] = pet_with_desc
        return jsonify({"success": True})

    return jsonify({"success": False}), 500

# Endpoint: GET /pets/favorites - get favorite pets from local cache
@app.route("/pets/favorites", methods=["GET"])
async def get_favorites():
    async with favorites_cache_lock:
        favorites_list = list(favorites_cache.values())
    return jsonify({"favorites": favorites_list})

# Endpoint: POST /pets/favorites/add - add pet to favorites locally
@app.route("/pets/favorites/add", methods=["POST"])
async def add_favorite():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"success": False, "error": "Invalid or missing petId"}), 400

    # Check pet exists in cache or fetch from Petstore
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)

    if not pet:
        pet_raw = await petstore_get(f"/pet/{pet_id}")
        if not pet_raw or pet_raw.get("id") != pet_id:
            return jsonify({"success": False, "error": "Pet not found"}), 404
        pet = add_fun_description(pet_raw)
        async with pets_cache_lock:
            pets_cache[pet_id] = pet

    async with favorites_cache_lock:
        favorites_cache[pet_id] = pet

    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```