```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache for pets keyed by petId (simulate persistence)
local_pet_cache: Dict[int, dict] = {}

# In-memory job status cache for async operations
entity_jobs: Dict[str, dict] = {}

# External Petstore API base URL (Swagger Petstore public API)
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"


async def fetch_pets_from_external(filters: dict) -> list:
    """
    Search pets by filters calling external Petstore API.
    Petstore API doesn't provide direct search by filters in GET/POST,
    so we fetch all pets by status and filter locally.
    TODO: Improve search if external API supports advanced queries.
    """
    try:
        status = filters.get("status")
        type_filter = filters.get("type")
        name_filter = filters.get("name", "").lower()

        # Petstore API allows get pets by status: available, pending, sold
        # We'll fetch by status if given, else fetch 'available' as default
        status_to_fetch = status if status in {"available", "pending", "sold"} else "available"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status_to_fetch})
            resp.raise_for_status()
            pets = resp.json()

        # Filter pets by type and name locally
        filtered = []
        for pet in pets:
            if type_filter and pet.get("category", {}).get("name", "").lower() != type_filter.lower():
                continue
            if name_filter and name_filter not in pet.get("name", "").lower():
                continue
            filtered.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": status_to_fetch,
                "photoUrls": pet.get("photoUrls", []),
            })
        return filtered

    except Exception as e:
        logger.exception("Failed fetching pets from external API")
        return []


async def add_pet_external(pet_data: dict) -> Optional[int]:
    """
    Add new pet to external Petstore API.
    Returns new pet ID if successful.
    """
    try:
        # Petstore expects payload with id, category, name, photoUrls, status, tags
        # We'll generate a temporary random id for demo, in real usage server assigns id.
        # TODO: Ideally get an ID from external API response, here we simulate with timestamp
        pet_id = int(datetime.utcnow().timestamp() * 1000)

        payload = {
            "id": pet_id,
            "category": {"id": 0, "name": pet_data.get("type", "unknown")},
            "name": pet_data["name"],
            "photoUrls": pet_data.get("photoUrls", []),
            "tags": [],
            "status": pet_data.get("status", "available"),
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{PETSTORE_API_BASE}/pet", json=payload)
            resp.raise_for_status()

        return pet_id
    except Exception as e:
        logger.exception("Failed adding pet to external API")
        return None


async def update_pet_status_external(pet_id: int, status: str) -> bool:
    """
    Update pet status in external Petstore API.
    Petstore API supports update via form data.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{PETSTORE_API_BASE}/pet/{pet_id}",
                data={"status": status}
            )
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.exception(f"Failed updating pet status for pet_id={pet_id}")
        return False


# Async job processor pattern for long-running external calls
async def process_entity_job(job_id: str, task_coro):
    try:
        entity_jobs[job_id]["status"] = "processing"
        await task_coro
        entity_jobs[job_id]["status"] = "done"
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed")


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    data = await request.get_json(force=True)
    job_id = f"search-{datetime.utcnow().isoformat()}"

    async def task():
        pets = await fetch_pets_from_external(data)
        # Cache results locally keyed by pet id for quick GET access later
        for pet in pets:
            local_pet_cache[pet["id"]] = pet
        entity_jobs[job_id]["result"] = pets

    entity_jobs[job_id] = {"status": "created", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity_job(job_id, task()))

    return jsonify({"jobId": job_id, "status": entity_jobs[job_id]["status"]})


@app.route("/pets/search/status/<job_id>", methods=["GET"])
async def search_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "done":
        return jsonify({"status": job["status"], "pets": job.get("result", [])})
    else:
        return jsonify({"status": job["status"]})


@app.route("/pets", methods=["POST"])
async def add_pet():
    data = await request.get_json(force=True)
    job_id = f"add-{datetime.utcnow().isoformat()}"

    async def task():
        pet_id = await add_pet_external(data)
        if pet_id:
            pet = {
                "id": pet_id,
                "name": data["name"],
                "type": data.get("type"),
                "status": data.get("status", "available"),
                "photoUrls": data.get("photoUrls", []),
            }
            local_pet_cache[pet_id] = pet
            entity_jobs[job_id]["result"] = {"id": pet_id, "message": "Pet added successfully"}
        else:
            entity_jobs[job_id]["result"] = {"error": "Failed to add pet"}

    entity_jobs[job_id] = {"status": "created", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity_job(job_id, task()))

    return jsonify({"jobId": job_id, "status": entity_jobs[job_id]["status"]})


@app.route("/pets/add/status/<job_id>", methods=["GET"])
async def add_pet_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "done":
        return jsonify({"status": job["status"], **job.get("result", {})})
    else:
        return jsonify({"status": job["status"]})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = local_pet_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found in local cache"}), 404
    return jsonify(pet)


@app.route("/pets/<int:pet_id>/status", methods=["POST"])
async def update_pet_status(pet_id):
    data = await request.get_json(force=True)
    new_status = data.get("status")
    if new_status not in {"available", "pending", "sold"}:
        return jsonify({"error": "Invalid status value"}), 400

    job_id = f"update-status-{datetime.utcnow().isoformat()}"

    async def task():
        success = await update_pet_status_external(pet_id, new_status)
        if success:
            # Update local cache if pet exists
            pet = local_pet_cache.get(pet_id)
            if pet:
                pet["status"] = new_status
            entity_jobs[job_id]["result"] = {"id": pet_id, "message": "Status updated successfully"}
        else:
            entity_jobs[job_id]["result"] = {"error": "Failed to update status"}

    entity_jobs[job_id] = {"status": "created", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity_job(job_id, task()))

    return jsonify({"jobId": job_id, "status": entity_jobs[job_id]["status"]})


@app.route("/pets/update-status/status/<job_id>", methods=["GET"])
async def update_status_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "done":
        return jsonify({"status": job["status"], **job.get("result", {})})
    else:
        return jsonify({"status": job["status"]})


if __name__ == '__main__':
    import sys
    import logging.config

    # Simple console logging config
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
