from dataclasses import dataclass
from typing import Optional, List
import asyncio
import logging
import random
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class FetchPetsRequest:
    type: Optional[str]
    status: Optional[str]

@dataclass
class RandomPetRequest:
    type: Optional[str]

@dataclass
class QueryPetsRequest:
    type: Optional[str]
    status: Optional[str]

# In-memory async-safe cache
class PetStoreCache:
    def __init__(self):
        self._pets = []
        self._lock = asyncio.Lock()

    async def set_pets(self, pets: List[dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self, pet_type: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        async with self._lock:
            pets = self._pets
            if pet_type:
                pets = [p for p in pets if p.get("type") == pet_type]
            if status:
                pets = [p for p in pets if p.get("status") == status]
            return pets

    async def get_pet_by_id(self, pet_id: int) -> Optional[dict]:
        async with self._lock:
            return next((p for p in self._pets if p.get("id") == pet_id), None)

    async def get_random_pet(self, pet_type: Optional[str] = None) -> Optional[dict]:
        pets = await self.get_pets(pet_type=pet_type)
        return random.choice(pets) if pets else None

cache = PetStoreCache()
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

def normalize_pet_data(raw_pet: dict) -> dict:
    pet_type = raw_pet.get("category", {}).get("name") if raw_pet.get("category") else None
    tags = [t["name"] for t in raw_pet.get("tags", [])] if raw_pet.get("tags") else []
    return {
        "id": raw_pet.get("id"),
        "name": raw_pet.get("name"),
        "type": pet_type,
        "status": raw_pet.get("status"),
        "tags": tags,
        "photoUrls": raw_pet.get("photoUrls", []),
    }

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            if status:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
                resp.raise_for_status()
                pets_raw = resp.json()
            else:
                pets_raw = []
                for s in ["available", "pending", "sold"]:
                    resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": s})
                    resp.raise_for_status()
                    pets_raw.extend(resp.json())
            pets = [normalize_pet_data(p) for p in pets_raw]
            if pet_type:
                pets = [p for p in pets if p.get("type") == pet_type]
            return pets
        except Exception as e:
            logger.exception(e)
            return []

async def process_pet_fetch_job(pet_type: Optional[str], status: Optional[str]):
    logger.info(f"Started pet fetch job type={pet_type} status={status}")
    pets = await fetch_pets_from_petstore(pet_type, status)
    await cache.set_pets(pets)
    logger.info(f"Fetched and stored {len(pets)} pets")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # validation last for POST due to quart-schema defect workaround
async def pets_fetch(data: FetchPetsRequest):
    requested_at = datetime.utcnow().isoformat()
    asyncio.create_task(process_pet_fetch_job(data.type, data.status))
    return jsonify({
        "message": "Pets fetch job started",
        "requestedAt": requested_at
    })

@validate_querystring(QueryPetsRequest)  # validation first for GET due to quart-schema defect workaround
@app.route("/pets", methods=["GET"])
async def pets_list(query_args: QueryPetsRequest):
    pets = await cache.get_pets(pet_type=query_args.type, status=query_args.status)
    return jsonify(pets)

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_company_lei(id: str):
    # No validation needed for this GET with path param
    return jsonify({"id": id, "lei": "TODO: lookup LEI"})

@app.route("/pets/random", methods=["POST"])
@validate_request(RandomPetRequest)  # validation last for POST due to quart-schema defect workaround
async def pets_random(data: RandomPetRequest):
    pet = await cache.get_random_pet(pet_type=data.type)
    if pet:
        return jsonify(pet)
    return jsonify({"message": "No pet found matching criteria"}), 404

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    pet = await cache.get_pet_by_id(pet_id)
    if pet:
        return jsonify(pet)
    return jsonify({"message": "Pet not found"}), 404

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)