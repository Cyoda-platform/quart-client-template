from dataclasses import dataclass
from typing import List, Optional
import asyncio
import logging
from datetime import datetime
import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# dataclasses for request validation
@dataclass
class SearchFilters:
    type: Optional[str]
    status: Optional[str]
    name: Optional[str]

@dataclass
class AddPet:
    name: str
    type: Optional[str]
    status: Optional[str]
    photoUrls: List[str]

@dataclass
class UpdateStatus:
    status: str

local_pet_cache: dict = {}
entity_jobs: dict = {}
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_external(filters: dict) -> list:
    try:
        status = filters.get("status")
        type_filter = filters.get("type")
        name_filter = filters.get("name", "").lower()
        status_to_fetch = status if status in {"available","pending","sold"} else "available"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status_to_fetch})
            resp.raise_for_status()
            pets = resp.json()
        filtered = []
        for pet in pets:
            if type_filter and pet.get("category",{}).get("name","").lower() != type_filter.lower():
                continue
            if name_filter and name_filter not in pet.get("name","").lower():
                continue
            filtered.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category",{}).get("name"),
                "status": status_to_fetch,
                "photoUrls": pet.get("photoUrls",[]),
            })
        return filtered
    except Exception as e:
        logger.exception("Failed fetching pets from external API")
        return []

async def add_pet_external(pet_data: dict) -> Optional[int]:
    try:
        pet_id = int(datetime.utcnow().timestamp() * 1000)
        payload = {
            "id": pet_id,
            "category": {"id":0,"name":pet_data.get("type","unknown")},
            "name":pet_data["name"],
            "photoUrls":pet_data.get("photoUrls",[]),
            "tags":[],
            "status":pet_data.get("status","available"),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{PETSTORE_API_BASE}/pet", json=payload)
            resp.raise_for_status()
        return pet_id
    except Exception as e:
        logger.exception("Failed adding pet to external API")
        return None

async def update_pet_status_external(pet_id: int, status: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{PETSTORE_API_BASE}/pet/{pet_id}", data={"status": status})
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.exception(f"Failed updating pet status for pet_id={pet_id}")
        return False

async def process_entity_job(job_id: str, task_coro):
    try:
        entity_jobs[job_id]["status"] = "processing"
        await task_coro
        entity_jobs[job_id]["status"] = "done"
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchFilters)  # validation after route due to POST defect workaround
async def search_pets(data: SearchFilters):
    job_id = f"search-{datetime.utcnow().isoformat()}"
    async def task():
        pets = await fetch_pets_from_external(data.__dict__)
        for pet in pets:
            local_pet_cache[pet["id"]] = pet
        entity_jobs[job_id]["result"] = pets
    entity_jobs[job_id] = {"status":"created","requestedAt":datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity_job(job_id, task()))
    return jsonify({"jobId":job_id,"status":entity_jobs[job_id]["status"]})

@app.route("/pets/search/status/<job_id>", methods=["GET"])
async def search_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error":"Job not found"}),404
    if job["status"]=="done":
        return jsonify({"status":job["status"],"pets":job.get("result",[])})
    return jsonify({"status":job["status"]})

@app.route("/pets", methods=["POST"])
@validate_request(AddPet)  # validation after route due to POST defect workaround
async def add_pet(data: AddPet):
    job_id = f"add-{datetime.utcnow().isoformat()}"
    async def task():
        pet_id = await add_pet_external(data.__dict__)
        if pet_id:
            pet = {"id":pet_id,"name":data.name,"type":data.type,"status":data.status,"photoUrls":data.photoUrls}
            local_pet_cache[pet_id] = pet
            entity_jobs[job_id]["result"] = {"id":pet_id,"message":"Pet added successfully"}
        else:
            entity_jobs[job_id]["result"] = {"error":"Failed to add pet"}
    entity_jobs[job_id] = {"status":"created","requestedAt":datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity_job(job_id, task()))
    return jsonify({"jobId":job_id,"status":entity_jobs[job_id]["status"]})

@app.route("/pets/add/status/<job_id>", methods=["GET"])
async def add_pet_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error":"Job not found"}),404
    if job["status"]=="done":
        return jsonify({"status":job["status"],**job.get("result",{})})
    return jsonify({"status":job["status"]})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = local_pet_cache.get(pet_id)
    if not pet:
        return jsonify({"error":"Pet not found in local cache"}),404
    return jsonify(pet)

@app.route("/pets/<int:pet_id>/status", methods=["POST"])
@validate_request(UpdateStatus)  # validation after route due to POST defect workaround
async def update_pet_status(pet_id, data: UpdateStatus):
    new_status = data.status
    if new_status not in {"available","pending","sold"}:
        return jsonify({"error":"Invalid status value"}),400
    job_id = f"update-status-{datetime.utcnow().isoformat()}"
    async def task():
        success = await update_pet_status_external(pet_id, new_status)
        if success:
            pet = local_pet_cache.get(pet_id)
            if pet:
                pet["status"] = new_status
            entity_jobs[job_id]["result"] = {"id":pet_id,"message":"Status updated successfully"}
        else:
            entity_jobs[job_id]["result"] = {"error":"Failed to update status"}
    entity_jobs[job_id] = {"status":"created","requestedAt":datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity_job(job_id, task()))
    return jsonify({"jobId":job_id,"status":entity_jobs[job_id]["status"]})

@app.route("/pets/update-status/status/<job_id>", methods=["GET"])
async def update_status_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error":"Job not found"}),404
    if job["status"]=="done":
        return jsonify({"status":job["status"],**job.get("result",{})})
    return jsonify({"status":job["status"]})

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)