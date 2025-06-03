from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request models
@dataclass
class SearchParams:
    type: str
    status: str
    tags: List[str] = None

@dataclass
class AddPet:
    name: str
    type: str
    status: str
    tags: List[str]
    description: str

@dataclass
class UpdatePet:
    id: int
    name: str
    status: str

@dataclass
class DeletePet:
    id: int

# In-memory async-safe cache for pet data and jobs
pets_cache: Dict[int, Dict[str, Any]] = {}
pets_cache_lock = asyncio.Lock()

entity_jobs: Dict[str, Dict[str, Any]] = {}
entity_jobs_lock = asyncio.Lock()

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"
PETSTORE_PETS_ENDPOINT = f"{PETSTORE_BASE}/pet"

next_local_pet_id = 100000

async def fetch_petstore_pets(params: Dict[str, Any]) -> list:
    status = params.get("status")
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    query_params = {}
    if status:
        query_params["status"] = status
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=query_params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore: {e}")
            return []
    pet_type = params.get("type")
    tags_filter = params.get("tags") or []
    def pet_matches(pet):
        if pet_type and pet_type != "all":
            if pet.get("category", {}).get("name", "").lower() != pet_type.lower():
                return False
        if tags_filter:
            pet_tags = [tag.get("name", "").lower() for tag in pet.get("tags", [])]
            if not all(t.lower() in pet_tags for t in tags_filter):
                return False
        return True
    filtered = [pet for pet in pets if pet_matches(pet)]
    result = []
    for pet in filtered:
        result.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", "").lower(),
            "status": pet.get("status"),
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
            "description": pet.get("name") + " is a lovely pet."
        })
    return result

async def add_pet_to_petstore(pet_data: Dict[str, Any]) -> int:
    global next_local_pet_id
    async with pets_cache_lock:
        next_local_pet_id += 1
        pet_id = next_local_pet_id
    pet_payload = {
        "id": pet_id,
        "category": {"id": 0, "name": pet_data.get("type", "unknown")},
        "name": pet_data.get("name", "Unnamed"),
        "photoUrls": [],
        "tags": [{"id": 0, "name": tag} for tag in pet_data.get("tags", [])],
        "status": pet_data.get("status", "available")
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(PETSTORE_PETS_ENDPOINT, json=pet_payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.exception(f"Error adding pet to Petstore: {e}")
            raise
    async with pets_cache_lock:
        pets_cache[pet_id] = {
            "id": pet_id,
            "name": pet_payload["name"],
            "type": pet_payload["category"]["name"],
            "status": pet_payload["status"],
            "tags": pet_data.get("tags", []),
            "description": pet_data.get("description", "")
        }
    return pet_id

async def update_pet_in_petstore(pet_data: Dict[str, Any]) -> bool:
    pet_id = pet_data.get("id")
    if not pet_id:
        raise ValueError("Pet ID is required for update")
    async with pets_cache_lock:
        cached = pets_cache.get(pet_id, {})
    payload = {
        "id": pet_id,
        "category": {"id": 0, "name": pet_data.get("type", cached.get("type", "unknown"))},
        "name": pet_data.get("name", cached.get("name", "Unnamed")),
        "photoUrls": [],
        "tags": [{"id": 0, "name": tag} for tag in pet_data.get("tags", cached.get("tags", []))],
        "status": pet_data.get("status", cached.get("status", "available"))
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.put(PETSTORE_PETS_ENDPOINT, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.exception(f"Error updating pet in Petstore: {e}")
            raise
    async with pets_cache_lock:
        pets_cache[pet_id] = {
            "id": pet_id,
            "name": payload["name"],
            "type": payload["category"]["name"],
            "status": payload["status"],
            "tags": pet_data.get("tags", cached.get("tags", [])),
            "description": pet_data.get("description", cached.get("description", ""))
        }
    return True

async def delete_pet_in_petstore(pet_id: int) -> bool:
    url = f"{PETSTORE_PETS_ENDPOINT}/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.exception(f"Error deleting pet in Petstore: {e}")
            raise
    async with pets_cache_lock:
        pets_cache.pop(pet_id, None)
    return True

async def process_search(entity_job: Dict[str, Any], params: Dict[str, Any]):
    try:
        pets = await fetch_petstore_pets(params)
        async with pets_cache_lock:
            for pet in pets:
                pets_cache[pet["id"]] = pet
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"pets": pets}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_add(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        pet_id = await add_pet_to_petstore(data)
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"success": True, "petId": pet_id}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_update(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        success = await update_pet_in_petstore(data)
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"success": success}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_delete(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        pet_id = data.get("id")
        if pet_id is None:
            raise ValueError("Pet ID missing for delete")
        success = await delete_pet_in_petstore(pet_id)
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"success": success}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

def generate_job_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchParams)  # workaround: place last for POST due to library defect
async def pets_search(data: SearchParams):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_search(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPet)  # workaround: place last for POST due to library defect
async def pets_add(data: AddPet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_add(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/update", methods=["POST"])
@validate_request(UpdatePet)  # workaround: place last for POST due to library defect
async def pets_update(data: UpdatePet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_update(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/delete", methods=["POST"])
@validate_request(DeletePet)  # workaround: place last for POST due to library defect
async def pets_delete(data: DeletePet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_delete(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    async with entity_jobs_lock:
        job = entity_jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)