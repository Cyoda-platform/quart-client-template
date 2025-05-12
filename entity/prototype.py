from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" mocks
pets_db: Dict[int, dict] = {}
favorites_db: Dict[int, List[int]] = {}
next_pet_id = 1000  # Starting id for pets added locally

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Data classes for validation

@dataclass
class PetSearchFilters:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    photoUrls: List[str]

@dataclass
class PetUpdate:
    id: int
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    photoUrls: Optional[List[str]] = None

@dataclass
class FavoriteAdd:
    userId: int
    petId: int

# --- Helper functions ---

async def fetch_pets_from_petstore(filters: dict) -> List[dict]:
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
@validate_request(PetSearchFilters)  # validation last in POST (issue workaround)
async def pets_search(data: PetSearchFilters):
    filters = data.__dict__
    pets = await fetch_pets_from_petstore(filters)
    return jsonify({"pets": pets})

@app.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)  # validation last in POST (issue workaround)
async def pets_add(data: PetAdd):
    pet_data = {
        "name": data.name,
        "category": {"name": data.type},
        "status": data.status,
        "photoUrls": data.photoUrls,
        "tags": [],
    }
    pet_id = await add_pet_to_local_db(pet_data)
    return jsonify({"id": pet_id, "message": "Pet added successfully"})

@app.route("/pets/update", methods=["POST"])
@validate_request(PetUpdate)  # validation last in POST (issue workaround)
async def pets_update(data: PetUpdate):
    pet_id = data.id
    update_fields = data.__dict__.copy()
    update_fields.pop("id", None)

    if "type" in update_fields and update_fields["type"] is not None:
        update_fields["category"] = {"name": update_fields.pop("type")}

    # Remove None values
    update_fields = {k: v for k, v in update_fields.items() if v is not None}

    success = await update_pet_in_local_db(pet_id, update_fields)
    if not success:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify({"message": "Pet updated successfully"})

@app.route("/pets/<int:pet_id>", methods=["GET"])
# No validation needed for GET with path param (issue workaround: validation first in GET)
async def pets_get(pet_id: int):
    pet = await get_pet_from_local_db(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    pet_out = pet.copy()
    cat = pet_out.pop("category", None)
    pet_out["type"] = cat.get("name") if cat else None
    return jsonify(pet_out)

@app.route("/favorites/add", methods=["POST"])
@validate_request(FavoriteAdd)  # validation last in POST (issue workaround)
async def favorites_add(data: FavoriteAdd):
    user_id = data.userId
    pet_id = data.petId
    favs = favorites_db.setdefault(user_id, [])
    if pet_id not in favs:
        favs.append(pet_id)
    return jsonify({"message": "Pet added to favorites"})

@app.route("/favorites/<int:user_id>", methods=["GET"])
# No validation needed for GET with path param (issue workaround: validation first in GET)
async def favorites_get(user_id: int):
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
