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

# Simple in-memory cache for pet details after search
pet_cache: Dict[int, Dict] = {}

# Entity job tracking for async processing (mock pattern)
entity_jobs: Dict[str, Dict] = {}

PETSTORE_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    """
    Fetch pets from Petstore API applying filters.
    Petstore API does not support direct filtering by status/type on search,
    so we fetch all pets with given status and filter client-side.
    """
    try:
        status = filters.get("status", "available")
        url = f"{PETSTORE_BASE}/pet/findByStatus?status={status}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching pets from Petstore: {e}")
        return []

    # Filter by type and name client-side (Petstore pets have 'category' key with 'name' for type)
    filtered = []
    pet_type = filters.get("type", "all").lower()
    name = filters.get("name", "").lower()

    for pet in pets:
        # Petstore pet "type" is category.name
        p_type = pet.get("category", {}).get("name", "").lower()
        if pet_type != "all" and p_type != pet_type:
            continue
        if name and name not in (pet.get("name") or "").lower():
            continue
        filtered.append(pet)

    return filtered


async def enrich_with_fun_fact(pet: Dict) -> Dict:
    """
    Add a funFact field to pet dict.
    TODO: Could be improved with a real fun fact source or algorithm.
    """
    fun_facts = {
        "cat": "Cats sleep for 70% of their lives!",
        "dog": "Dogs have three eyelids.",
    }
    p_type = pet.get("category", {}).get("name", "").lower()
    pet["funFact"] = fun_facts.get(p_type, "Pets bring joy to life!")
    return pet


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Receives filters, fetches pets from Petstore API, caches results, returns list.
    """
    data = await request.get_json(force=True)
    filters = {
        "type": data.get("type", "all"),
        "status": data.get("status", "available"),
        "name": data.get("name", ""),
    }

    requested_at = datetime.utcnow().isoformat()
    job_id = f"search-{requested_at}"

    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget processing
    asyncio.create_task(process_search_job(job_id, filters))

    return jsonify({"jobId": job_id, "status": "processing"}), 202


async def process_search_job(job_id: str, filters: Dict):
    try:
        pets = await fetch_pets_from_petstore(filters)

        # Cache pets by id for quick GET detail retrieval
        for pet in pets:
            pet_cache[pet["id"]] = pet

        entity_jobs[job_id]["status"] = "done"
        entity_jobs[job_id]["result"] = {
            "pets": [
                {
                    "id": pet["id"],
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls", []),
                }
                for pet in pets
            ]
        }
        logger.info(f"Search job {job_id} completed with {len(pets)} pets")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Error processing search job {job_id}: {e}")


@app.route("/pets/recommendation", methods=["POST"])
async def pets_recommendation():
    """
    POST /pets/recommendation
    Returns fun pet recommendations based on preferredType and mood.
    """
    data = await request.get_json(force=True)
    preferred_type = data.get("preferredType", "all").lower()
    # Mood is currently unused, placeholder for future logic
    mood = data.get("mood", "fun")

    # Fetch pets with preferredType and status available
    filters = {"type": preferred_type, "status": "available"}

    pets = await fetch_pets_from_petstore(filters)

    # Pick up to 3 random pets for recommendation
    # TODO: Improve with smarter recommendation logic
    pets = pets[:3]

    # Add fun facts
    enriched_pets = []
    for pet in pets:
        pet_with_fact = await enrich_with_fun_fact(pet)
        enriched_pets.append(
            {
                "id": pet_with_fact["id"],
                "name": pet_with_fact.get("name"),
                "type": pet_with_fact.get("category", {}).get("name"),
                "status": pet_with_fact.get("status"),
                "funFact": pet_with_fact.get("funFact"),
            }
        )

    return jsonify({"recommendedPets": enriched_pets})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    """
    GET /pets/{id}
    Returns cached pet detail if available.
    """
    pet = pet_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found or not cached"}), 404

    # Compose response with description as placeholder
    response = {
        "id": pet["id"],
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "description": "A lovely pet looking for a home!",  # TODO: Add real description if available
    }
    return jsonify(response)


@app.route("/jobs/<job_id>", methods=["GET"])
async def job_status(job_id: str):
    """
    GET /jobs/{job_id}
    Returns status and result of async jobs like /pets/search
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
