```python
import asyncio
import logging
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory "cache" for pets by ID
# Key: pet_id (int), Value: pet data dict
pets_cache: Dict[int, dict] = {}
pets_cache_lock = asyncio.Lock()

PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Helper to generate unique IDs for added pets locally (simulate Petstore behavior)
next_local_pet_id = 100000  # start from a high number to avoid collision with real petstore IDs
pets_local_id_lock = asyncio.Lock()


async def fetch_petstore_pets(filters: dict):
    """
    Query Petstore API by status to get pets.
    Petstore API supports filtering pets by status (available, pending, sold).
    We will filter by type and name locally.
    """
    status = filters.get("status")
    if status not in ("available", "pending", "sold"):
        status = "available"  # default fallback to available

    url = f"{PETSTORE_BASE}/pet/findByStatus?status={status}"

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception("Error fetching pets from Petstore API")
            return []

    # Filter by type and name locally
    type_filter = filters.get("type", "all")
    name_filter = filters.get("name", "").lower()

    def pet_matches(pet):
        pet_type = None
        # Petstore pets have category field: {"id":..., "name":"dog"} or "cat"
        if pet.get("category") and pet["category"].get("name"):
            pet_type = pet["category"]["name"].lower()
        else:
            pet_type = "unknown"

        if type_filter != "all" and pet_type != type_filter:
            return False
        if name_filter and name_filter not in (pet.get("name") or "").lower():
            return False
        return True

    filtered = [p for p in pets if pet_matches(p)]

    # Normalize pet data (id, name, type, status, photoUrls)
    normalized = []
    for p in filtered:
        normalized.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": (p.get("category") or {}).get("name", "unknown"),
                "status": p.get("status"),
                "photoUrls": p.get("photoUrls", []),
            }
        )
    return normalized


async def add_pet_to_petstore(pet_data: dict):
    """
    Send POST /pet to Petstore API to add pet.
    Returns the created pet ID or None on error.
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{PETSTORE_BASE}/pet", json=pet_data, timeout=10)
            r.raise_for_status()
            created_pet = r.json()
            return created_pet.get("id")
        except Exception as e:
            logger.exception("Error adding pet to Petstore API")
            return None


async def update_pet_in_petstore(pet_id: int, pet_data: dict):
    """
    Send PUT /pet to Petstore API to update pet.
    Petstore API expects entire pet object with id.
    """
    pet_data["id"] = pet_id
    async with httpx.AsyncClient() as client:
        try:
            r = await client.put(f"{PETSTORE_BASE}/pet", json=pet_data, timeout=10)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Error updating pet in Petstore API")
            return False


async def delete_pet_in_petstore(pet_id: int):
    """
    Send DELETE /pet/{petId} to Petstore API.
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.delete(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Error deleting pet in Petstore API")
            return False


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    # Validate basic presence of fields (dynamic, so no schema validation)
    type_filter = data.get("type", "all")
    status_filter = data.get("status", None)
    name_filter = data.get("name", "")

    # Fetch from Petstore API and filter
    pets = await fetch_petstore_pets(
        {"type": type_filter, "status": status_filter, "name": name_filter}
    )

    # Update cache with fetched pets (async-safe)
    async with pets_cache_lock:
        for pet in pets:
            pets_cache[pet["id"]] = pet

    return jsonify({"pets": pets})


@app.route("/pets/add", methods=["POST"])
async def pets_add():
    data = await request.get_json(force=True)
    # Required fields: name, type, status, photoUrls
    pet_name = data.get("name")
    pet_type = data.get("type")
    pet_status = data.get("status")
    photo_urls = data.get("photoUrls", [])

    if not pet_name or pet_type not in ("cat", "dog") or pet_status not in (
        "available",
        "pending",
        "sold",
    ):
        return jsonify({"message": "Invalid input"}), 400

    # Petstore expects category object for type
    petstore_pet = {
        "name": pet_name,
        "category": {"id": 0, "name": pet_type},
        "photoUrls": photo_urls,
        "status": pet_status,
    }

    # Add pet to Petstore API
    pet_id = await add_pet_to_petstore(petstore_pet)
    if not pet_id:
        return jsonify({"message": "Failed to add pet"}), 500

    # Update cache
    petstore_pet["id"] = pet_id
    async with pets_cache_lock:
        pets_cache[pet_id] = petstore_pet

    return jsonify({"message": "Pet added successfully", "petId": pet_id})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get(pet_id):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
        # Try fetching from Petstore API as fallback
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
                if r.status_code == 200:
                    p = r.json()
                    pet = {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "type": (p.get("category") or {}).get("name", "unknown"),
                        "status": p.get("status"),
                        "photoUrls": p.get("photoUrls", []),
                    }
                    # Cache it
                    async with pets_cache_lock:
                        pets_cache[pet_id] = pet
                else:
                    return jsonify({"message": "Pet not found"}), 404
            except Exception as e:
                logger.exception("Error fetching pet detail from Petstore API")
                return jsonify({"message": "Error fetching pet data"}), 500

    return jsonify(pet)


@app.route("/pets/update/<int:pet_id>", methods=["POST"])
async def pets_update(pet_id):
    data = await request.get_json(force=True)
    # Allowed update fields: name, status, photoUrls (type is immutable here)
    # Fetch existing pet from cache or Petstore API
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)

    if not pet:
        # Try fetch from Petstore API
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
                if r.status_code == 200:
                    p = r.json()
                    pet = {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "type": (p.get("category") or {}).get("name", "unknown"),
                        "status": p.get("status"),
                        "photoUrls": p.get("photoUrls", []),
                    }
                else:
                    return jsonify({"message": "Pet not found"}), 404
            except Exception as e:
                logger.exception("Error fetching pet for update")
                return jsonify({"message": "Error fetching pet data"}), 500

    # Prepare updated pet data for Petstore API
    updated_pet = {
        "id": pet_id,
        "name": data.get("name", pet["name"]),
        "category": {"id": 0, "name": pet["type"]},
        "status": data.get("status", pet["status"]),
        "photoUrls": data.get("photoUrls", pet.get("photoUrls", [])),
    }

    success = await update_pet_in_petstore(pet_id, updated_pet)
    if not success:
        return jsonify({"message": "Failed to update pet"}), 500

    # Update cache
    async with pets_cache_lock:
        pets_cache[pet_id] = {
            "id": pet_id,
            "name": updated_pet["name"],
            "type": pet["type"],
            "status": updated_pet["status"],
            "photoUrls": updated_pet["photoUrls"],
        }

    return jsonify({"message": "Pet updated successfully"})


@app.route("/pets/delete/<int:pet_id>", methods=["POST"])
async def pets_delete(pet_id):
    # Delete pet via Petstore API
    success = await delete_pet_in_petstore(pet_id)
    if not success:
        return jsonify({"message": "Failed to delete pet"}), 500

    # Remove from cache
    async with pets_cache_lock:
        pets_cache.pop(pet_id, None)

    return jsonify({"message": "Pet deleted successfully"})


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
