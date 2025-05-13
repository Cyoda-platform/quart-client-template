import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: validate_request must come last on POST, and first on GET due to quart-schema defect

# Request models
@dataclass
class PetSearchRequest:
    type: Optional[str]
    status: Optional[str]
    name: Optional[str]

@dataclass
class AddPetRequest:
    name: str
    type: str
    status: str
    # photoUrls handling is unclear; using comma-separated string as placeholder
    photoUrls: Optional[str] = None  # TODO: handle list of URLs properly

@dataclass
class UpdatePetRequest:
    name: Optional[str]
    type: Optional[str]
    status: Optional[str]
    photoUrls: Optional[str] = None  # TODO: handle list of URLs properly

# Local in-memory cache for pets added/updated/deleted locally
local_pets: Dict[int, Dict] = {}
local_pet_id_counter = 1

# Cache for last fetched external pets by search parameters (simplified)
external_pets_cache: Dict[str, List[Dict]] = {}

# Petstore API base URL
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

# Lock for local_pets id generation (async safe)
local_pets_lock = asyncio.Lock()

def make_cache_key(filters: Dict) -> str:
    key = "|".join(f"{k}={v}" for k, v in sorted(filters.items()) if v)
    return key or "all"

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def search_pets(data: PetSearchRequest):
    filters = {
        "type": data.type,
        "status": data.status,
        "name": data.name,
    }
    cache_key = make_cache_key(filters)
    if cache_key in external_pets_cache:
        logger.info(f"Returning cached external pets for key: {cache_key}")
        return jsonify({"pets": external_pets_cache[cache_key]})

    pets = []
    async with httpx.AsyncClient() as client:
        try:
            if data.status:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": data.status})
                r.raise_for_status()
                pets = r.json()
            else:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": "available"})
                r.raise_for_status()
                pets = r.json()

            if data.type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == data.type.lower()]
            if data.name:
                pets = [p for p in pets if data.name.lower() in p.get("name", "").lower()]
        except Exception as e:
            logger.exception(e)
            return jsonify({"pets": [], "error": "Failed to fetch pets from Petstore API"}), 500

    simplified = []
    for p in pets:
        simplified.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        })

    external_pets_cache[cache_key] = simplified
    return jsonify({"pets": simplified})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = local_pets.get(pet_id)
    if pet:
        return jsonify(pet)
    for pets_list in external_pets_cache.values():
        for p in pets_list:
            if p["id"] == pet_id:
                return jsonify(p)
    return jsonify({"error": "Pet not found"}), 404

@app.route("/pets", methods=["POST"])
@validate_request(AddPetRequest)
async def add_pet(data: AddPetRequest):
    if not data.name or not data.type or not data.status:
        return jsonify({"error": "Missing required fields: name, type, status"}), 400
    async with local_pets_lock:
        global local_pet_id_counter
        pet_id = local_pet_id_counter
        local_pet_id_counter += 1
        local_pets[pet_id] = {
            "id": pet_id,
            "name": data.name,
            "type": data.type,
            "status": data.status,
            "photoUrls": data.photoUrls.split(",") if data.photoUrls else [],
        }
    logger.info(f"Added local pet {pet_id}: {data.name}")
    return jsonify({"id": pet_id, "message": "Pet added successfully"}), 201

@app.route("/pets/<int:pet_id>/update", methods=["POST"])
@validate_request(UpdatePetRequest)
async def update_pet(data: UpdatePetRequest, pet_id: int):
    pet = local_pets.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    if data.name is not None:
        pet["name"] = data.name
    if data.type is not None:
        pet["type"] = data.type
    if data.status is not None:
        pet["status"] = data.status
    if data.photoUrls is not None:
        pet["photoUrls"] = data.photoUrls.split(",")
    logger.info(f"Updated local pet {pet_id}")
    return jsonify({"message": "Pet updated successfully"})

@app.route("/pets/<int:pet_id>/delete", methods=["POST"])
async def delete_pet(pet_id: int):
    pet = local_pets.pop(pet_id, None)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    logger.info(f"Deleted local pet {pet_id}")
    return jsonify({"message": "Pet deleted successfully"})

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)