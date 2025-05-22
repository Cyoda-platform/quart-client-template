import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Optional, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Async-safe in-memory cache
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._store = {}

    async def set(self, key, value):
        async with self._lock:
            self._store[key] = value

    async def get(self, key):
        async with self._lock:
            return self._store.get(key)

    async def update(self, key, update_dict):
        async with self._lock:
            if key in self._store:
                self._store[key].update(update_dict)
                return True
            return False

search_cache = AsyncCache()
pet_cache = AsyncCache()
pet_id_seq = asyncio.Lock()
pet_id_counter = 0

async def generate_pet_id():
    global pet_id_counter
    async with pet_id_seq:
        pet_id_counter += 1
        return pet_id_counter

PETSTORE_BASE = "https://petstore.swagger.io/v2"

@dataclass
class PetSearch:
    type: Optional[str]
    status: Optional[str]

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    tags: Optional[List[str]]

@dataclass
class PetUpdate:
    name: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)  # workaround: validate_request last for POST
async def pets_search(data: PetSearch):
    pet_type = data.type
    status = data.status

    params = {}
    if status:
        params["status"] = status
    else:
        params["status"] = "available"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets_raw = resp.json()

        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        pets = []
        for p in pets_filtered:
            pets.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name", "unknown"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")] if p.get("tags") else []
            })

        search_id = str(uuid.uuid4())
        await search_cache.set(search_id, pets)
        logger.info(f"Stored search results under searchId={search_id}, count={len(pets)}")

        return jsonify({"searchId": search_id})

    except httpx.HTTPError as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets from Petstore API"}), 502

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    pets = await search_cache.get(search_id)
    if pets is None:
        return jsonify({"error": "searchId not found"}), 404
    return jsonify({"pets": pets})

@app.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)  # workaround: validate_request last for POST
async def add_pet(data: PetAdd):
    if not data.name or not data.type or not data.status:
        return jsonify({"error": "Missing required fields: name, type, status"}), 400

    pet_id = await generate_pet_id()
    pet_data = {
        "id": pet_id,
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "tags": data.tags or [],
    }

    await pet_cache.set(pet_id, pet_data)
    message = f"🐾 Purrfect! Pet '{data.name}' with ID {pet_id} has been added to your collection! 🐱"
    logger.info(f"Added new pet: {pet_data}")

    return jsonify({"petId": pet_id, "message": message})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = await pet_cache.get(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/update/<int:pet_id>", methods=["POST"])
@validate_request(PetUpdate)  # workaround: validate_request last for POST
async def update_pet(data: PetUpdate, pet_id):
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.status is not None:
        update_data["status"] = data.status
    if data.tags is not None:
        update_data["tags"] = data.tags

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    updated = await pet_cache.update(pet_id, update_data)
    if not updated:
        return jsonify({"error": "Pet not found"}), 404

    message = f"🐾 Pet ID {pet_id} updated with love and care! 💖"
    logger.info(f"Updated pet {pet_id} with {update_data}")

    return jsonify({"message": message})

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s',
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)