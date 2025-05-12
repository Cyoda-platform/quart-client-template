```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "cache" and adoption registry
pets_cache: Dict[int, Dict[str, Any]] = {}
adoptions: Dict[int, Dict[str, Any]] = {}

# Simulated entity jobs for async processing
entity_jobs: Dict[str, Dict[str, Any]] = {}

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Helper to fetch pets from external API with filters
async def fetch_pets_from_external(type_: str = None, status: str = None, limit: int = 10):
    query_params = {}
    if status:
        query_params["status"] = status
    # Petstore API uses "findByStatus" endpoint that accepts multiple statuses comma separated.
    # There's no direct "type" filter, so we will filter manually after fetching.
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            pets = response.json()
        except Exception as e:
            logger.exception(e)
            return []

    # Filter by type if requested (Petstore API does not support type filtering)
    if type_:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == type_.lower()]

    # Limit results
    return pets[:limit]


# Async processing task for pet search POST
async def process_pet_search(job_id: str, data: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_external(
            type_=data.get("type"),
            status=data.get("status"),
            limit=data.get("limit", 10),
        )
        # Store in cache by pet ID
        for pet in pets:
            pets_cache[pet["id"]] = {
                "id": pet["id"],
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "description": pet.get("tags")[0]["name"] if pet.get("tags") else "",
            }
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = pets
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    job_id = f"search-{datetime.utcnow().isoformat()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget async processing
    asyncio.create_task(process_pet_search(job_id, data))
    # Immediately return job status and id
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/pets/search/result/<job_id>", methods=["GET"])
async def pets_search_result(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    if job["status"] == "processing":
        return jsonify({"status": "processing"}), 202
    if job["status"] == "failed":
        return jsonify({"status": "failed", "error": job.get("error")}), 500
    # Return processed pets summary (id, name, type, status, description)
    results = [
        {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("type"),
            "status": pet.get("status"),
            "description": pet.get("description"),
        }
        for pet in job.get("result", [])
    ]
    return jsonify({"results": results})


@app.route("/pets/adopt", methods=["POST"])
async def pets_adopt():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    adopter_name = data.get("adopterName")
    adopter_contact = data.get("adopterContact")

    if not pet_id or not adopter_name or not adopter_contact:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    # Check pet exists in cache or fetch from external API as fallback (sync here for simplicity)
    pet = pets_cache.get(pet_id)
    if not pet:
        # TODO: improve fallback by async fetch (simplified sync for prototype)
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                r.raise_for_status()
                pet_data = r.json()
                pet = {
                    "id": pet_data.get("id"),
                    "name": pet_data.get("name"),
                    "type": pet_data.get("category", {}).get("name"),
                    "status": pet_data.get("status"),
                    "description": pet_data.get("tags")[0]["name"] if pet_data.get("tags") else "",
                }
                pets_cache[pet_id] = pet
            except Exception as e:
                logger.exception(e)
                return jsonify({"success": False, "message": "Pet not found"}), 404

    # Register adoption (mock persistence)
    adoptions[pet_id] = {
        "pet": pet,
        "adopterName": adopter_name,
        "adopterContact": adopter_contact,
        "adoptedAt": datetime.utcnow().isoformat(),
    }

    # Update pet status locally to "adopted" (mock)
    pets_cache[pet_id]["status"] = "adopted"

    return jsonify({"success": True, "message": "Adoption request registered"})


@app.route("/pets", methods=["GET"])
async def pets_list():
    # Return pets from cache + adoption info
    pets_list = []
    for pet in pets_cache.values():
        pets_list.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("type"),
                "status": pet.get("status"),
            }
        )
    return jsonify({"pets": pets_list})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id):
    pet = pets_cache.get(pet_id)
    if not pet:
        # Try to fetch from external API (sync for simplicity)
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                r.raise_for_status()
                pet_data = r.json()
                pet = {
                    "id": pet_data.get("id"),
                    "name": pet_data.get("name"),
                    "type": pet_data.get("category", {}).get("name"),
                    "status": pet_data.get("status"),
                    "description": pet_data.get("tags")[0]["name"] if pet_data.get("tags") else "",
                    "adoptionStatus": "available",
                }
                pets_cache[pet_id] = pet
            except Exception as e:
                logger.exception(e)
                return jsonify({"error": "Pet not found"}), 404

    adoption_status = "adopted" if pet_id in adoptions else pet.get("status", "unknown")
    pet_detail = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("type"),
        "status": pet.get("status"),
        "description": pet.get("description"),
        "adoptionStatus": adoption_status,
    }
    return jsonify(pet_detail)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
