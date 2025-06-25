from dataclasses import dataclass
from typing import Optional, List
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

favorites_lock = asyncio.Lock()
favorites_cache: Dict[int, dict] = {}

@dataclass
class PetSearch:
    status: Optional[str]
    type: Optional[str]

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    photoUrls: List[str]

@dataclass
class PetUpdate:
    id: int
    name: Optional[str]
    status: Optional[str]
    photoUrls: Optional[List[str]]
    type: Optional[str]

@dataclass
class PetId:
    id: int

# Utility functions ...

async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            status_param = status if status else "available"
            response = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status_param})
            response.raise_for_status()
            pets = response.json()
            if pet_type:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pets: {e}")
            return []

async def add_pet_to_petstore(pet_data: dict) -> Optional[int]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{PETSTORE_API_BASE}/pet", json=pet_data)
            response.raise_for_status()
            pet = response.json()
            return pet.get("id")
        except httpx.HTTPError as e:
            logger.exception(f"Error adding pet: {e}")
            return None

async def update_pet_in_petstore(pet_data: dict) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(f"{PETSTORE_API_BASE}/pet", json=pet_data)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.exception(f"Error updating pet: {e}")
            return False

async def delete_pet_from_petstore(pet_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.exception(f"Error deleting pet: {e}")
            return False

@app.route("/pets/search", methods=["POST"])
# Workaround for quart-schema validate_request defect: validation decorator last for POST
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    pets = await fetch_pets_from_petstore(data.status, data.type)
    result = []
    for pet in pets:
        result.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", [])
        })
    return jsonify({"pets": result})

@app.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)
async def pets_add(data: PetAdd):
    pet_payload = {
        "name": data.name,
        "photoUrls": data.photoUrls,
        "status": data.status,
        "category": {"id": 0, "name": data.type},
    }
    pet_id = await add_pet_to_petstore(pet_payload)
    if pet_id is None:
        return jsonify({"success": False}), 500
    return jsonify({"success": True, "petId": pet_id})

@app.route("/pets/update", methods=["POST"])
@validate_request(PetUpdate)
async def pets_update(data: PetUpdate):
    if not data.id:
        return jsonify({"success": False, "error": "Missing pet id"}), 400
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{data.id}")
            resp.raise_for_status()
            pet = resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet: {e}")
            return jsonify({"success": False, "error": "Pet not found"}), 404
    if data.name: pet["name"] = data.name
    if data.status: pet["status"] = data.status
    if data.photoUrls: pet["photoUrls"] = data.photoUrls
    if data.type: pet["category"] = {"id": 0, "name": data.type}
    success = await update_pet_in_petstore(pet)
    if not success:
        return jsonify({"success": False}), 500
    return jsonify({"success": True})

@app.route("/pets/delete", methods=["POST"])
@validate_request(PetId)
async def pets_delete(data: PetId):
    success = await delete_pet_from_petstore(data.id)
    if not success:
        return jsonify({"success": False}), 500
    return jsonify({"success": True})

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    async with favorites_lock:
        favs = list(favorites_cache.values())
    return jsonify({"favorites": favs})

@app.route("/pets/favorites/add", methods=["POST"])
@validate_request(PetId)
async def pets_favorites_add(data: PetId):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{data.id}")
            resp.raise_for_status()
            pet = resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet: {e}")
            return jsonify({"success": False, "error": "Pet not found"}), 404
    pet_fav = {"id": pet.get("id"), "name": pet.get("name"), "type": pet.get("category", {}).get("name", ""), "status": pet.get("status")}
    async with favorites_lock:
        favorites_cache[data.id] = pet_fav
    return jsonify({"success": True})

@app.route("/pets/favorites/remove", methods=["POST"])
@validate_request(PetId)
async def pets_favorites_remove(data: PetId):
    async with favorites_lock:
        favorites_cache.pop(data.id, None)
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)