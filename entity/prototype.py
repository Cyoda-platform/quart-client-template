```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for pets data keyed by pet id
pets_cache: Dict[int, dict] = {}

# Entity job status store for example async processing tracking
entity_jobs: Dict[str, dict] = {}

# External Petstore API base URL
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[dict]:
    """
    Fetch pets from external Petstore API filtered by type and status.
    """
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    else:
        params["status"] = "available"  # default filter to avoid empty result
    
    # Petstore API requires status param; type will be filtered client side
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            # Filter client side by type if given
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
    except Exception as e:
        logger.exception("Error fetching pets from Petstore API")
        return []


async def calculate_match_score(pet: dict, preferred_type: Optional[str], preferred_status: Optional[str]) -> float:
    """
    Simple matchmaking scoring logic based on matching type and status.
    Returns a float score 0-1.
    """
    score = 0.0
    if preferred_type and pet.get("category", {}).get("name", "").lower() == preferred_type.lower():
        score += 0.6
    if preferred_status and pet.get("status", "").lower() == preferred_status.lower():
        score += 0.4
    return score


async def process_fetch_pets_job(job_id: str, pet_type: Optional[str], status: Optional[str]):
    """
    Background task: fetch pets and update cache.
    """
    entity_jobs[job_id]["status"] = "processing"
    try:
        pets = await fetch_pets_from_petstore(pet_type, status)
        # Update cache
        for pet in pets:
            pets_cache[pet["id"]] = pet
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"count": len(pets)}
        logger.info(f"Fetched and cached {len(pets)} pets for job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception("Failed to process fetch pets job")


async def process_matchmake_job(job_id: str, preferred_type: Optional[str], preferred_status: Optional[str]):
    """
    Background task: fetch pets (if needed) and calculate matchmaking scores.
    """
    entity_jobs[job_id]["status"] = "processing"
    try:
        # For demo simplicity, fetch fresh data each time
        pets = await fetch_pets_from_petstore(preferred_type, preferred_status)

        matched_pets = []
        for pet in pets:
            score = await calculate_match_score(pet, preferred_type, preferred_status)
            if score > 0:
                p = pet.copy()
                p["matchScore"] = round(score, 2)
                matched_pets.append(p)

        # Update cache with fetched pets (optional)
        for pet in pets:
            pets_cache[pet["id"]] = pet

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"matchedPets": matched_pets}
        logger.info(f"Matchmaking completed with {len(matched_pets)} matches for job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception("Failed to process matchmaking job")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Request:
    {
        "type": "string",   // optional
        "status": "string"  // optional
    }
    Response: cached pet list after fetch
    """
    data = await request.get_json()
    pet_type = data.get("type")
    status = data.get("status")

    job_id = f"fetch-{datetime.utcnow().isoformat()}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget background fetch job
    asyncio.create_task(process_fetch_pets_job(job_id, pet_type, status))

    return jsonify({"jobId": job_id, "status": "started"}), 202


@app.route("/pets/matchmake", methods=["POST"])
async def pets_matchmake():
    """
    POST /pets/matchmake
    Request:
    {
        "preferredType": "string",    // optional
        "preferredStatus": "string"   // optional
    }
    Response: matched pets with scores
    """
    data = await request.get_json()
    preferred_type = data.get("preferredType")
    preferred_status = data.get("preferredStatus")

    job_id = f"matchmake-{datetime.utcnow().isoformat()}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget background matchmaking job
    asyncio.create_task(process_matchmake_job(job_id, preferred_type, preferred_status))

    return jsonify({"jobId": job_id, "status": "started"}), 202


@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    GET /pets
    Return cached pets.
    """
    return jsonify({"pets": list(pets_cache.values())})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    """
    GET /pets/{id}
    Return cached pet details with optional fun description.
    """
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    pet_detail = pet.copy()
    # TODO: Add real fun facts or description generation here
    pet_detail["description"] = f"Meet {pet_detail.get('name', 'this pet')}! A lovely {pet_detail.get('category', {}).get('name', 'pet')} waiting for a new home."

    return jsonify(pet_detail)


@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    """
    Optional: Endpoint to check status/results of background jobs.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
