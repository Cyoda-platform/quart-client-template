from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # validate_querystring imported if needed later

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class AdoptPetRequest:
    petId: int

pets_cache: Dict[int, dict] = {}
adopt_status: Dict[int, str] = {}

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(
    type_filter: Optional[str] = None, status_filter: Optional[str] = None
) -> List[dict]:
    status = status_filter or "available"
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore API: {e}")
            return []
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets

async def update_pet_adoption_status_in_petstore(pet_id: int) -> bool:
    get_url = f"{PETSTORE_BASE}/pet/{pet_id}"
    update_url = f"{PETSTORE_BASE}/pet"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(get_url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if not pet:
                logger.info(f"Pet ID {pet_id} not found in Petstore.")
                return False
            pet["status"] = "adopted"
            resp_update = await client.put(update_url, json=pet, timeout=10)
            resp_update.raise_for_status()
            return True
        except Exception as e:
            logger.exception(f"Failed to update adoption status in Petstore for pet {pet_id}: {e}")
            return False

async def process_fetch_pets(data: dict):
    pets = await fetch_pets_from_petstore(
        type_filter=data.get("type"),
        status_filter=data.get("status"),
    )
    for pet in pets:
        pet_id = pet.get("id")
        if not pet_id:
            continue
        pets_cache[pet_id] = pet
        adopt_status[pet_id] = pet.get("status", "available")

async def process_adopt_pet(pet_id: int) -> bool:
    success = await update_pet_adoption_status_in_petstore(pet_id)
    if success:
        adopt_status[pet_id] = "adopted"
        if pet_id in pets_cache:
            pets_cache[pet_id]["status"] = "adopted"
    return success

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # workaround: validation must be last for POST due to quart-schema defect
async def fetch_pets(data: FetchPetsRequest):
    asyncio.create_task(process_fetch_pets(data.__dict__))
    return jsonify({"message": "Pet data fetch started. Please GET /pets to see cached results."}), 202

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)  # workaround: validation must be last for POST due to quart-schema defect
async def adopt_pet(data: AdoptPetRequest):
    pet_id = data.petId
    if pet_id not in pets_cache:
        return jsonify({"error": f"Pet with ID {pet_id} not found in local cache. Please fetch pets first."}), 404
    success = await process_adopt_pet(pet_id)
    if not success:
        return jsonify({"error": "Failed to adopt pet via external API."}), 500
    return jsonify({"message": f"Pet with ID {pet_id} has been adopted."})

@app.route("/pets", methods=["GET"])
async def get_pets():
    pets_list = []
    for pet_id, pet in pets_cache.items():
        pet_copy = pet.copy()
        pet_copy["status"] = adopt_status.get(pet_id, pet_copy.get("status", "unknown"))
        pets_list.append(pet_copy)
    return jsonify({"pets": pets_list})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": f"Pet with ID {pet_id} not found in local cache."}), 404
    pet_copy = pet.copy()
    pet_copy["status"] = adopt_status.get(pet_id, pet_copy.get("status", "unknown"))
    return jsonify(pet_copy)

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)