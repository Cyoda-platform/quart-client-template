from dataclasses import dataclass
from typing import Optional, List

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

# In-memory cache
pets_cache = {}
entity_jobs = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

def next_pet_id() -> int:
    if pets_cache:
        return max(pets_cache.keys()) + 1
    return 1000

async def fetch_pets_from_petstore(filter_status, filter_category):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": filter_status or "available"}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if filter_category:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == filter_category.lower()]
            return pets
        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            return []

async def process_fetch_pets_job(job_id, status, category):
    try:
        pets = await fetch_pets_from_petstore(status, category)
        pets_cache.clear()
        for pet in pets:
            pid = pet.get("id")
            if not pid:
                continue
            pets_cache[pid] = {
                "id": pid,
                "name": pet.get("name"),
                "category": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "tags": [t.get("name") for t in pet.get("tags", []) if t.get("name")]
            }
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["pets_count"] = len(pets_cache)
        logger.info(f"Fetch pets job {job_id} completed.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Fetch pets job {job_id} failed.")

@dataclass
class Filter:
    status: str
    category: Optional[str] = None

@dataclass
class FetchPetsRequest:
    filter: Filter

@dataclass
class AddPetRequest:
    name: str
    category: str
    status: str
    tags: List[str]

@dataclass
class UpdatePetRequest:
    name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # Workaround: validate_request after route due to quart-schema defect
async def pets_fetch(data: FetchPetsRequest):
    status = data.filter.status
    category = data.filter.category
    job_id = f"fetch_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_fetch_pets_job(job_id, status, category))
    return jsonify({"message": "Data fetch initiated", "job_id": job_id})

@app.route("/pets", methods=["GET"])
async def list_pets():
    return jsonify(list(pets_cache.values()))

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)  # Workaround: validate_request after route due to quart-schema defect
async def add_pet(data: AddPetRequest):
    pet_id = next_pet_id()
    pets_cache[pet_id] = {
        "id": pet_id,
        "name": data.name,
        "category": data.category,
        "status": data.status,
        "tags": data.tags,
    }
    logger.info(f"Added pet {pet_id}")
    return jsonify({"message": "Pet added successfully", "pet_id": pet_id})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/update/<int:pet_id>", methods=["POST"])
@validate_request(UpdatePetRequest)  # Workaround: validate_request after route due to quart-schema defect
async def update_pet(data: UpdatePetRequest, pet_id):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    if data.name is not None:
        pet["name"] = data.name
    if data.category is not None:
        pet["category"] = data.category
    if data.status is not None:
        pet["status"] = data.status
    if data.tags is not None:
        pet["tags"] = data.tags
    pets_cache[pet_id] = pet
    logger.info(f"Updated pet {pet_id}")
    return jsonify({"message": "Pet updated successfully"})

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)