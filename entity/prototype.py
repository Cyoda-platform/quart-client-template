```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "cache" for pets by ID and jobs
pets_cache: Dict[int, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Helper for generating IDs for pets added locally (simulate DB auto-increment)
local_pet_id_sequence = 1
local_pet_id_lock = asyncio.Lock()


async def fetch_pet_from_external(pet_id: int) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            data = resp.json()
            # Cache the pet locally for GET usage
            pets_cache[pet_id] = data
            return data
        except httpx.HTTPStatusError as e:
            logger.exception(f"Pet not found in external API: {pet_id}")
            raise
        except Exception as e:
            logger.exception("Unexpected error fetching pet from external API")
            raise


async def process_search(criteria: Dict[str, Any]) -> None:
    """
    Fire and forget processing of pet search.
    Place results in entity_jobs under the job_id.
    """
    job_id = criteria.get("job_id")
    try:
        async with httpx.AsyncClient() as client:
            # Build query params according to Petstore API spec
            # Petstore search endpoint: /pet/findByStatus or /pet/findByTags
            # We'll do a simple findByStatus if status provided, else fetch all (mock limitation)
            status = criteria.get("status")
            type_ = criteria.get("type")  # Petstore API does not support filtering by type, so we filter locally
            name = criteria.get("name")  # Also filtered locally

            pets = []
            if status:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            else:
                # No status filter, get all statuses (available, pending, sold)
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": "available,pending,sold"})

            resp.raise_for_status()
            pets_data = resp.json()

            # Filter by type and name locally
            for pet in pets_data:
                if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
                    continue
                if name and name.lower() not in pet.get("name", "").lower():
                    continue
                pets.append({
                    "id": pet["id"],
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls", []),
                })

            # Store results in job
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"pets": pets}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception("Error processing pet search")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)


async def process_add_pet(data: Dict[str, Any], job_id: str) -> None:
    """
    Fire and forget adding a pet.
    We simulate adding to external API by POST /pet.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "name": data.get("name"),
                "photoUrls": data.get("photoUrls", []),
                "status": data.get("status"),
                "category": {"name": data.get("type")} if data.get("type") else None,
                "id": None  # Let petstore assign
            }
            # Remove None keys
            if payload["category"] is None:
                payload.pop("category")

            resp = await client.post(f"{PETSTORE_API_BASE}/pet", json=payload)
            resp.raise_for_status()
            pet_resp = resp.json()

            # Cache locally
            pets_cache[pet_resp["id"]] = pet_resp

            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {
                "id": pet_resp["id"],
                "message": "Pet added successfully"
            }
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error adding pet")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)


async def process_update_pet(data: Dict[str, Any], job_id: str) -> None:
    """
    Fire and forget updating a pet.
    Uses PUT /pet.
    """
    try:
        pet_id = data.get("id")
        if pet_id is None:
            raise ValueError("Pet id is required for update")

        async with httpx.AsyncClient() as client:
            payload = {
                "id": pet_id,
                "name": data.get("name"),
                "photoUrls": data.get("photoUrls", []),
                "status": data.get("status"),
                "category": {"name": data.get("type")} if data.get("type") else None,
            }
            # Remove keys with None to avoid overwriting
            payload = {k: v for k, v in payload.items() if v is not None}
            if "category" in payload and payload["category"] is None:
                payload.pop("category")

            resp = await client.put(f"{PETSTORE_API_BASE}/pet", json=payload)
            resp.raise_for_status()
            pet_resp = resp.json()

            # Update local cache
            pets_cache[pet_id] = pet_resp

            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"message": "Pet updated successfully"}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error updating pet")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)


async def process_delete_pet(data: Dict[str, Any], job_id: str) -> None:
    """
    Fire and forget deleting a pet.
    Uses DELETE /pet/{petId}.
    """
    try:
        pet_id = data.get("id")
        if pet_id is None:
            raise ValueError("Pet id is required for delete")

        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()

            # Remove from local cache if present
            pets_cache.pop(pet_id, None)

            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"message": "Pet deleted successfully"}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error deleting pet")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    job_id = f"search_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Add job_id into criteria for process func
    data["job_id"] = job_id
    # Fire and forget
    asyncio.create_task(process_search(data))
    return jsonify({"job_id": job_id}), 202


@app.route("/pets/add", methods=["POST"])
async def pets_add():
    data = await request.get_json(force=True)
    job_id = f"add_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    asyncio.create_task(process_add_pet(data, job_id))
    return jsonify({"job_id": job_id}), 202


@app.route("/pets/update", methods=["POST"])
async def pets_update():
    data = await request.get_json(force=True)
    job_id = f"update_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    asyncio.create_task(process_update_pet(data, job_id))
    return jsonify({"job_id": job_id}), 202


@app.route("/pets/delete", methods=["POST"])
async def pets_delete():
    data = await request.get_json(force=True)
    job_id = f"delete_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    asyncio.create_task(process_delete_pet(data, job_id))
    return jsonify({"job_id": job_id}), 202


@app.route("/pets/job_status/<job_id>", methods=["GET"])
async def job_status(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    # First check local cache
    pet = pets_cache.get(pet_id)
    if pet:
        return jsonify(pet)

    # Fetch from external API and cache
    try:
        pet = await fetch_pet_from_external(pet_id)
        return jsonify(pet)
    except httpx.HTTPStatusError:
        return jsonify({"error": "Pet not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to retrieve pet"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
