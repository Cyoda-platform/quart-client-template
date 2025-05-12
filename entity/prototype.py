from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

pets_cache: Dict[int, Dict[str, Any]] = {}
next_pet_id = 1000
entity_job: Dict[str, Dict[str, Any]] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


@dataclass
class PetFilter:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None


@dataclass
class PetCreate:
    name: str
    type: str
    status: str = "available"
    category: str = "pets"
    photoUrls: List[str] = field(default_factory=list)


@dataclass
class PetUpdate:
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    photoUrls: Optional[List[str]] = None


async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    status = filters.get("status", "available")
    params = {"status": status}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()

            filtered = []
            pet_type = filters.get("type")
            name = filters.get("name")

            for pet in pets:
                if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
                    continue
                if name and name.lower() not in pet.get("name", "").lower():
                    continue
                filtered.append(pet)

            for pet in filtered:
                pets_cache[pet["id"]] = pet

            return {"pets": filtered}

    except Exception as e:
        logger.exception(e)
        return {"pets": []}


@app.route("/pets/search", methods=["POST"])
@validate_request(PetFilter)  # POST validation last per workaround
async def search_pets(data: PetFilter):
    filters = data.__dict__
    job_id = str(datetime.utcnow().timestamp())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    async def process_search():
        result = await fetch_pets_from_petstore(filters)
        entity_job[job_id]["status"] = "done"
        entity_job[job_id]["result"] = result

    asyncio.create_task(process_search())

    await asyncio.sleep(1)
    result = entity_job[job_id].get("result", {"pets": []})
    return jsonify(result)


@app.route("/pets/<int:pet_id>", methods=["GET"])
# GET validation first per workaround - no validation needed here as no query params
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets", methods=["POST"])
@validate_request(PetCreate)  # POST validation last per workaround
async def create_pet(data: PetCreate):
    global next_pet_id
    next_pet_id += 1
    pet_id = next_pet_id

    pet = {
        "id": pet_id,
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "category": data.category,
        "photoUrls": data.photoUrls,
    }
    pets_cache[pet_id] = pet

    return jsonify({"id": pet_id, "message": "Pet created successfully"}), 201


@app.route("/pets/<int:pet_id>", methods=["POST"])
@validate_request(PetUpdate)  # POST validation last per workaround
async def update_pet(pet_id: int, data: PetUpdate):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    if data.name is not None:
        pet["name"] = data.name
    if data.type is not None:
        pet["type"] = data.type
    if data.status is not None:
        pet["status"] = data.status
    if data.category is not None:
        pet["category"] = data.category
    if data.photoUrls is not None:
        pet["photoUrls"] = data.photoUrls

    pets_cache[pet_id] = pet
    return jsonify({"id": pet_id, "message": "Pet updated successfully"})


@app.route("/pets/<int:pet_id>/delete", methods=["POST"])
# POST with no body, no validation decorator needed
async def delete_pet(pet_id: int):
    if pet_id not in pets_cache:
        return jsonify({"error": "Pet not found"}), 404

    del pets_cache[pet_id]
    return jsonify({"id": pet_id, "message": "Pet deleted successfully"})


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
