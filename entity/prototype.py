from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class PetSearchQuery:
    type: str = None
    status: str = None
    name: str = None

@dataclass
class NewPet:
    name: str
    type: str
    status: str
    photoUrls: List[str] = None

@dataclass
class PetStatusUpdate:
    status: str

# In-memory "local store" for pets
_local_pet_store: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

def generate_pet_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str], name: Optional[str]) -> List[Dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        pets = []
        try:
            if status:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
            else:
                pets_accum = []
                for st in ["available", "pending", "sold"]:
                    r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": st})
                    if r.status_code == 200:
                        pets_accum.extend(r.json())
                pets = pets_accum
            def pet_matches(pet):
                if type_:
                    pet_type = pet.get("category", {}).get("name", "")
                    if pet_type.lower() != type_.lower():
                        return False
                if name:
                    pet_name = pet.get("name", "")
                    if name.lower() not in pet_name.lower():
                        return False
                return True
            pets = [p for p in pets if pet_matches(p)]
            return pets
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

@app.route("/pets/search", methods=["POST"])
# workaround: validate_request should be last for POST due to quart-schema defect
@validate_request(PetSearchQuery)
async def search_pets(data: PetSearchQuery):
    pets = await fetch_pets_from_petstore(data.type, data.status, data.name)
    def map_pet(pet):
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "photoUrls": pet.get("photoUrls", []),
        }
    mapped_pets = [map_pet(p) for p in pets]
    return jsonify({"pets": mapped_pets})

@app.route("/pets", methods=["POST"])
# workaround: validate_request should be last for POST due to quart-schema defect
@validate_request(NewPet)
async def add_pet(data: NewPet):
    if not (data.name and data.type and data.status):
        return jsonify({"error": "Missing required fields: name, type, status"}), 400
    pet_id = generate_pet_id()
    pet_data = {
        "id": pet_id,
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "photoUrls": data.photoUrls or [],
    }
    _local_pet_store[pet_id] = pet_data
    logger.info(f"Pet added locally: {pet_id} - {data.name}")
    return jsonify({"id": pet_id, "message": "Pet added successfully"}), 201

@app.route("/pets", methods=["GET"])
async def get_all_pets():
    pets = list(_local_pet_store.values())
    return jsonify({"pets": pets})

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id):
    pet = _local_pet_store.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/<pet_id>/status", methods=["POST"])
# workaround: validate_request should be last for POST due to quart-schema defect
@validate_request(PetStatusUpdate)
async def update_pet_status(data: PetStatusUpdate, pet_id):
    pet = _local_pet_store.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    pet["status"] = data.status
    logger.info(f"Updated pet {pet_id} status to {data.status}")
    return jsonify({"id": pet_id, "message": "Status updated successfully"})

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)