from dataclasses import dataclass
from typing import List, Optional, Dict
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

# Data classes for request validation
@dataclass
class SearchPetsRequest:
    type: str
    status: Optional[str]
    name: Optional[str]

@dataclass
class AddPetRequest:
    name: str
    type: str
    status: str
    photoUrls: List[str]

@dataclass
class UpdatePetRequest:
    name: Optional[str]
    status: Optional[str]
    photoUrls: Optional[List[str]]

# In-memory cache and locks
pets_cache: Dict[int, dict] = {}
pets_cache_lock = asyncio.Lock()

PETSTORE_BASE = "https://petstore.swagger.io/v2"

async def fetch_petstore_pets(filters: dict):
    status = filters.get("status")
    if status not in ("available", "pending", "sold"):
        status = "available"
    url = f"{PETSTORE_BASE}/pet/findByStatus?status={status}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception("Error fetching pets from Petstore API")
            return []
    type_filter = filters.get("type", "all").lower()
    name_filter = (filters.get("name") or "").lower()
    def pet_matches(pet):
        pet_type = (pet.get("category") or {}).get("name", "").lower()
        if type_filter != "all" and pet_type != type_filter:
            return False
        if name_filter and name_filter not in (pet.get("name") or "").lower():
            return False
        return True
    filtered = [p for p in pets if pet_matches(p)]
    normalized = []
    for p in filtered:
        normalized.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": (p.get("category") or {}).get("name", "unknown"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        })
    return normalized

async def add_pet_to_petstore(pet_data: dict):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(f"{PETSTORE_BASE}/pet", json=pet_data, timeout=10)
            r.raise_for_status()
            created_pet = r.json()
            return created_pet.get("id")
        except Exception:
            logger.exception("Error adding pet to Petstore API")
            return None

async def update_pet_in_petstore(pet_id: int, pet_data: dict):
    pet_data["id"] = pet_id
    async with httpx.AsyncClient() as client:
        try:
            r = await client.put(f"{PETSTORE_BASE}/pet", json=pet_data, timeout=10)
            r.raise_for_status()
            return True
        except Exception:
            logger.exception("Error updating pet in Petstore API")
            return False

async def delete_pet_in_petstore(pet_id: int):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.delete(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
            r.raise_for_status()
            return True
        except Exception:
            logger.exception("Error deleting pet in Petstore API")
            return False

# Workaround: validate_request must be last decorator for POST due to quart-schema defect
@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPetsRequest)
async def pets_search(data: SearchPetsRequest):
    filters = {"type": data.type, "status": data.status, "name": data.name}
    pets = await fetch_petstore_pets(filters)
    async with pets_cache_lock:
        for pet in pets:
            pets_cache[pet["id"]] = pet
    return jsonify({"pets": pets})

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)
async def pets_add(data: AddPetRequest):
    if data.type not in ("cat", "dog") or data.status not in ("available", "pending", "sold"):
        return jsonify({"message": "Invalid input"}), 400
    petstore_pet = {
        "name": data.name,
        "category": {"id": 0, "name": data.type},
        "photoUrls": data.photoUrls,
        "status": data.status,
    }
    pet_id = await add_pet_to_petstore(petstore_pet)
    if not pet_id:
        return jsonify({"message": "Failed to add pet"}), 500
    petstore_pet["id"] = pet_id
    async with pets_cache_lock:
        pets_cache[pet_id] = petstore_pet
    return jsonify({"message": "Pet added successfully", "petId": pet_id})

# GET does not take a body; no validation needed
@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get(pet_id):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
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
                    async with pets_cache_lock:
                        pets_cache[pet_id] = pet
                else:
                    return jsonify({"message": "Pet not found"}), 404
            except Exception:
                logger.exception("Error fetching pet detail from Petstore API")
                return jsonify({"message": "Error fetching pet data"}), 500
    return jsonify(pet)

# Workaround: validate_request must be last decorator for POST due to quart-schema defect
@app.route("/pets/update/<int:pet_id>", methods=["POST"])
@validate_request(UpdatePetRequest)
async def pets_update(data: UpdatePetRequest, pet_id):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
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
            except Exception:
                logger.exception("Error fetching pet for update")
                return jsonify({"message": "Error fetching pet data"}), 500
    updated_pet = {
        "id": pet_id,
        "name": data.name or pet["name"],
        "category": {"id": 0, "name": pet["type"]},
        "status": data.status or pet["status"],
        "photoUrls": data.photoUrls or pet.get("photoUrls", []),
    }
    success = await update_pet_in_petstore(pet_id, updated_pet)
    if not success:
        return jsonify({"message": "Failed to update pet"}), 500
    async with pets_cache_lock:
        pets_cache[pet_id] = {
            "id": pet_id,
            "name": updated_pet["name"],
            "type": pet["type"],
            "status": updated_pet["status"],
            "photoUrls": updated_pet["photoUrls"],
        }
    return jsonify({"message": "Pet updated successfully"})

# POST delete has no body validation
@app.route("/pets/delete/<int:pet_id>", methods=["POST"])
async def pets_delete(pet_id):
    success = await delete_pet_in_petstore(pet_id)
    if not success:
        return jsonify({"message": "Failed to delete pet"}), 500
    async with pets_cache_lock:
        pets_cache.pop(pet_id, None)
    return jsonify({"message": "Pet deleted successfully"})

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)