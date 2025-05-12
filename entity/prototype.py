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

# In-memory "database" mocks
pets_db: Dict[int, dict] = {}
favorites_db: Dict[int, List[int]] = {}
next_pet_id = 1000  # Starting id for pets added locally

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# --- Helper functions ---


async def fetch_pets_from_petstore(filters: dict) -> List[dict]:
    """
    Query Petstore API to get pets by filters.
    Since Petstore doesn't support complex filters directly,
    we will fetch by status and filter locally as example.
    """
    pets = []
    status = filters.get("status", "available")
    type_filter = filters.get("type")
    name_filter = filters.get("name")

    url = f"{PETSTORE_API_BASE}/pet/findByStatus?status={status}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.exception(e)
            return []

    # Filter by type and name locally (Petstore pets have 'category' for type)
    for pet in data:
        pet_type = pet.get("category", {}).get("name", "").lower()
        pet_name = pet.get("name", "").lower()
        if type_filter and pet_type != type_filter.lower():
            continue
        if name_filter and name_filter.lower() not in pet_name:
            continue
        pets.append(pet)
    return pets


async def add_pet_to_local_db(pet_data: dict) -> int:
    global next_pet_id
    pet_id = next_pet_id
    next_pet_id += 1
    pet_data_copy = pet_data.copy()
    pet_data_copy["id"] = pet_id
    pets_db[pet_id] = pet_data_copy
    return pet_id


async def update_pet_in_local_db(pet_id: int, update_data: dict) -> bool:
    pet = pets_db.get(pet_id)
    if not pet:
        return False
    pet.update(update_data)
    pets_db[pet_id] = pet
    return True


async def get_pet_from_local_db(pet_id: int) -> Optional[dict]:
    return pets_db.get(pet_id)


# --- Routes ---


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Request: JSON with optional filters: type, status, name
    Response: JSON list of pets matching filters from Petstore API only (no local pets)
    """
    filters = await request.get_json(force=True)
    pets = await fetch_pets_from_petstore(filters)
    return jsonify({"pets": pets})


@app.route("/pets/add", methods=["POST"])
async def pets_add():
    """
    POST /pets/add
    Request: JSON pet data (name, type, status, photoUrls)
    Response: id assigned and confirmation message
    """
    data = await request.get_json(force=True)
    # Map "type" -> "category" for consistency with Petstore format
    pet_data = {
        "name": data.get("name"),
        "category": {"name": data.get("type")},
        "status": data.get("status"),
        "photoUrls": data.get("photoUrls", []),
        "tags": [],  # TODO: support tags if needed
    }
    pet_id = await add_pet_to_local_db(pet_data)
    return jsonify({"id": pet_id, "message": "Pet added successfully"})


@app.route("/pets/update", methods=["POST"])
async def pets_update():
    """
    POST /pets/update
    Request: JSON with id and fields to update (name, status, etc.)
    Response: confirmation message or error if pet not found
    """
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not pet_id:
        return jsonify({"error": "Missing pet id"}), 400

    update_fields = data.copy()
    update_fields.pop("id", None)

    # Normalize type to category.name if present
    if "type" in update_fields:
        update_fields["category"] = {"name": update_fields.pop("type")}

    success = await update_pet_in_local_db(pet_id, update_fields)
    if not success:
        return jsonify({"error": "Pet not found"}), 404

    return jsonify({"message": "Pet updated successfully"})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get(pet_id: int):
    """
    GET /pets/{id}
    Retrieve pet details by ID from local DB only.
    """
    pet = await get_pet_from_local_db(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    # Flatten category.name as type for response consistency
    pet_out = pet.copy()
    cat = pet_out.pop("category", None)
    pet_out["type"] = cat.get("name") if cat else None
    return jsonify(pet_out)


@app.route("/favorites/add", methods=["POST"])
async def favorites_add():
    """
    POST /favorites/add
    Request: JSON with userId and petId
    Response: confirmation message
    """
    data = await request.get_json(force=True)
    user_id = data.get("userId")
    pet_id = data.get("petId")
    if not user_id or not pet_id:
        return jsonify({"error": "Missing userId or petId"}), 400

    favs = favorites_db.setdefault(user_id, [])
    if pet_id not in favs:
        favs.append(pet_id)
    return jsonify({"message": "Pet added to favorites"})


@app.route("/favorites/<int:user_id>", methods=["GET"])
async def favorites_get(user_id: int):
    """
    GET /favorites/{userId}
    Returns list of favorite pets for the user.
    """
    pet_ids = favorites_db.get(user_id, [])
    pets = []
    for pid in pet_ids:
        pet = await get_pet_from_local_db(pid)
        if pet:
            pet_out = pet.copy()
            cat = pet_out.pop("category", None)
            pet_out["type"] = cat.get("name") if cat else None
            pets.append(pet_out)
    return jsonify({"userId": user_id, "favorites": pets})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
