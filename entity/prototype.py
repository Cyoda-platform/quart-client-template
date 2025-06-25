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

# External Petstore API base URL
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# In-memory local cache for favorites (simulate persistence)
# Use asyncio.Lock to protect concurrent access
favorites_lock = asyncio.Lock()
favorites_cache: Dict[int, dict] = {}

# Utility async function to fetch pets from external API with filters
async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            # Petstore API does not directly support filtering by type or status in a single call.
            # We will call /pet/findByStatus with status filter, then filter by type locally.
            status_param = status if status else "available"
            response = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status_param})
            response.raise_for_status()
            pets = response.json()
            if pet_type:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

# Utility async function to add pet to external Petstore API
async def add_pet_to_petstore(pet_data: dict) -> Optional[int]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{PETSTORE_API_BASE}/pet", json=pet_data)
            response.raise_for_status()
            pet = response.json()
            return pet.get("id")
        except httpx.HTTPError as e:
            logger.exception(f"Error adding pet to Petstore API: {e}")
            return None

# Utility async function to update pet in external Petstore API
async def update_pet_in_petstore(pet_data: dict) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(f"{PETSTORE_API_BASE}/pet", json=pet_data)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.exception(f"Error updating pet in Petstore API: {e}")
            return False

# Utility async function to delete pet from external Petstore API
async def delete_pet_from_petstore(pet_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.exception(f"Error deleting pet from Petstore API: {e}")
            return False

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    status = data.get("status")
    pet_type = data.get("type")

    pets = await fetch_pets_from_petstore(status, pet_type)

    # Normalize pets output fields as per spec (id, name, type, status, photoUrls)
    result = []
    for pet in pets:
        pet_id = pet.get("id")
        name = pet.get("name")
        status_ = pet.get("status")
        photoUrls = pet.get("photoUrls", [])
        category = pet.get("category", {})
        type_ = category.get("name", "") if category else ""

        result.append(
            {
                "id": pet_id,
                "name": name,
                "type": type_,
                "status": status_,
                "photoUrls": photoUrls,
            }
        )

    return jsonify({"pets": result})

@app.route("/pets/add", methods=["POST"])
async def pets_add():
    data = await request.get_json(force=True)
    # Petstore expects full pet object, including "category" with "id" and "name"
    # TODO: We assume the client sends "type" which is mapped to category name, but no category id.
    # Using 0 as placeholder category id.
    pet_payload = {
        "name": data.get("name"),
        "photoUrls": data.get("photoUrls", []),
        "status": data.get("status", "available"),
        "category": {
            "id": 0,
            "name": data.get("type", "")
        },
        # TODO: Tags omitted for simplicity
    }

    pet_id = await add_pet_to_petstore(pet_payload)
    if pet_id is None:
        return jsonify({"success": False}), 500
    return jsonify({"success": True, "petId": pet_id})

@app.route("/pets/update", methods=["POST"])
async def pets_update():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not pet_id:
        return jsonify({"success": False, "error": "Missing pet id"}), 400

    # We must send full pet object to Petstore PUT /pet, so fetch existing first
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet for update: {e}")
            return jsonify({"success": False, "error": "Pet not found"}), 404

    # Update fields from request data (only certain fields allowed)
    if "name" in data:
        pet["name"] = data["name"]
    if "status" in data:
        pet["status"] = data["status"]
    if "photoUrls" in data:
        pet["photoUrls"] = data["photoUrls"]
    if "type" in data:
        pet["category"] = {"id": 0, "name": data["type"]}

    success = await update_pet_in_petstore(pet)
    if not success:
        return jsonify({"success": False}), 500
    return jsonify({"success": True})

@app.route("/pets/delete", methods=["POST"])
async def pets_delete():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not pet_id:
        return jsonify({"success": False, "error": "Missing pet id"}), 400

    success = await delete_pet_from_petstore(pet_id)
    if not success:
        return jsonify({"success": False}), 500
    return jsonify({"success": True})

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    async with favorites_lock:
        favorites_list = list(favorites_cache.values())
    return jsonify({"favorites": favorites_list})

@app.route("/pets/favorites/add", methods=["POST"])
async def pets_favorites_add():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not pet_id:
        return jsonify({"success": False, "error": "Missing pet id"}), 400

    # Fetch pet info from Petstore to cache favorite details
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet for favorites add: {e}")
            return jsonify({"success": False, "error": "Pet not found"}), 404

    pet_fav = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", ""),
        "status": pet.get("status"),
    }

    async with favorites_lock:
        favorites_cache[pet_id] = pet_fav

    return jsonify({"success": True})

@app.route("/pets/favorites/remove", methods=["POST"])
async def pets_favorites_remove():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not pet_id:
        return jsonify({"success": False, "error": "Missing pet id"}), 400

    async with favorites_lock:
        if pet_id in favorites_cache:
            del favorites_cache[pet_id]

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
