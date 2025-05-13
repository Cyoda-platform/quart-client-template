from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: str
    status: str
    name: str = None

@dataclass
class AdoptRequest:
    petId: str
    adopterName: str
    contactInfo: str

pets_cache = {}
adoptions_cache = {}
pets_cache_lock = asyncio.Lock()
adoptions_cache_lock = asyncio.Lock()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(type_, status, name):
    params = {}
    if type_ and type_.lower() != "all":
        params["type"] = type_.lower()
    if status and status.lower() != "all":
        params["status"] = status.lower()
    status_param = params.get("status", "available")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status_param})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []
    filtered = []
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
        pet_name = pet.get("name", "").lower()
        if type_.lower() != "all" and pet_type != type_.lower():
            continue
        if name and name.lower() not in pet_name:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type or "unknown",
            "status": pet.get("status", ""),
            "description": pet.get("tags")[0]["name"] if pet.get("tags") else "",
            "imageUrl": pet.get("photoUrls")[0] if pet.get("photoUrls") else "",
        })
    return filtered

async def process_adoption(adoption_id, adoption_data):
    try:
        await asyncio.sleep(2)
        async with adoptions_cache_lock:
            adoptions_cache[adoption_id]["status"] = "approved"
        logger.info(f"Adoption {adoption_id} approved for pet {adoption_data['petId']}")
    except Exception as e:
        logger.exception(e)
        async with adoptions_cache_lock:
            adoptions_cache[adoption_id]["status"] = "error"

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)  # issue workaround: validator last on POST
async def pets_search(data: PetSearch):
    pets = await fetch_pets_from_petstore(data.type, data.status, data.name)
    async with pets_cache_lock:
        for pet in pets:
            pets_cache[pet["id"]] = pet
    return jsonify({"pets": pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)  # issue workaround: validator last on POST
async def pets_adopt(data: AdoptRequest):
    pet_id = data.petId
    adopter_name = data.adopterName
    contact_info = data.contactInfo

    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)

    if not pet:
        return jsonify({"message": "Pet not found or not cached; please search first"}), 404

    adoption_id = str(uuid4())
    requested_at = datetime.utcnow().isoformat()
    async with adoptions_cache_lock:
        adoptions_cache[adoption_id] = {
            "adoptionId": adoption_id,
            "petId": pet_id,
            "adopterName": adopter_name,
            "contactInfo": contact_info,
            "status": "pending",
            "requestedAt": requested_at,
        }
    asyncio.create_task(process_adoption(adoption_id, adoptions_cache[adoption_id]))
    return jsonify({"message": "Adoption request submitted successfully", "adoptionId": adoption_id})

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption(adoption_id):
    async with adoptions_cache_lock:
        adoption = adoptions_cache.get(adoption_id)
    if not adoption:
        return jsonify({"message": "Adoption request not found"}), 404
    return jsonify(adoption)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)