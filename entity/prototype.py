```python
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Union

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for pets and fun facts: 
# Structure: {pet_id: pet_data_with_fun_fact}
pets_store: Dict[str, Dict] = {}
# Job tracker for async processing (simulate entity workflow)
entity_jobs: Dict[str, Dict] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# --- Utility functions ---


def enrich_pets_with_fun_facts(pets: List[Dict]) -> List[Dict]:
    """Add funFact field to each pet, if missing add random placeholder."""
    fun_facts_samples = [
        "Loves catnip and naps.",
        "Can do a backflip!",
        "Enjoys long walks on the beach.",
        "Has a secret stash of toys.",
        "Purrs loudly when happy.",
    ]
    for pet in pets:
        if "funFact" not in pet or not pet["funFact"]:
            pet["funFact"] = random.choice(fun_facts_samples)
    return pets


async def fetch_pets_from_petstore(pet_type: str, limit: int) -> List[Dict]:
    """Fetch pets from Petstore API by type."""
    # Petstore API does not have filtering by type endpoint directly,
    # so we fetch all pets and filter client-side for prototype.
    url = f"{PETSTORE_API_BASE}/pet/findByStatus?status=available"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
            # Filter by pet_type if requested
            if pet_type in ("cat", "dog"):
                filtered = [
                    p for p in pets if pet_type.lower() in p.get("category", {}).get("name", "").lower()
                ]
            else:
                filtered = pets
            return filtered[:limit]
        except (httpx.HTTPError, KeyError) as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []


async def process_entity_job(job_id: str, pet_type: str, limit: int):
    """Simulate async processing: fetch, enrich, store pets."""
    try:
        pets = await fetch_pets_from_petstore(pet_type, limit)
        pets = enrich_pets_with_fun_facts(pets)
        # Store pets locally by pet id
        for pet in pets:
            pet_id = str(pet.get("id"))
            if pet_id:
                pets_store[pet_id] = pet
        entity_jobs[job_id]["status"] = "done"
        entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} finished processing {len(pets)} pets")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed: {e}")


# --- Routes ---


@app.route("/pets/list", methods=["POST"])
async def pets_list_post():
    """Fetch pets from external API and enrich them."""
    data = await request.get_json(force=True)
    pet_type = data.get("type", "all").lower()
    limit = data.get("limit", 10)
    if pet_type not in ("cat", "dog", "all"):
        return jsonify({"error": "Invalid type. Allowed: cat, dog, all"}), 400
    if not isinstance(limit, int) or limit <= 0:
        return jsonify({"error": "Limit must be positive integer"}), 400

    job_id = f"job-{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "pet_type": pet_type,
        "limit": limit,
    }

    # Fire-and-forget processing task
    asyncio.create_task(process_entity_job(job_id, pet_type, limit))

    return jsonify({"jobId": job_id, "status": "processing"}), 202


@app.route("/pets", methods=["GET"])
async def pets_get():
    """Return stored/enriched pets."""
    pets = list(pets_store.values())
    return jsonify({"pets": pets})


@app.route("/pets/funfact", methods=["POST"])
async def pets_funfact_post():
    """Add or update fun fact for a specific pet."""
    data = await request.get_json(force=True)
    pet_id = str(data.get("petId", "")).strip()
    fun_fact = data.get("funFact", "").strip()

    if not pet_id or not fun_fact:
        return jsonify({"error": "petId and funFact are required"}), 400

    pet = pets_store.get(pet_id)
    if not pet:
        return jsonify({"error": f"Pet with id {pet_id} not found"}), 404

    pet["funFact"] = fun_fact
    return jsonify({"success": True, "petId": pet_id, "funFact": fun_fact})


@app.route("/pets/random", methods=["GET"])
async def pets_random_get():
    """Return one random pet from stored pets."""
    pets = list(pets_store.values())
    if not pets:
        return jsonify({"error": "No pets available"}), 404
    pet = random.choice(pets)
    return jsonify({"pet": pet})


@app.route("/job/status/<job_id>", methods=["GET"])
async def job_status_get(job_id: str):
    """Optional: check processing job status."""
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
