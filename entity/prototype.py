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

# In-memory cache to mock persistence (per job and pet data)
entity_jobs: Dict[str, Dict[str, Any]] = {}
pet_cache: Dict[str, Dict[str, Any]] = {}  # keyed by pet id


async def fetch_all_pets_from_petstore() -> Dict[str, Any]:
    url = "https://petstore.swagger.io/v2/pet/findByStatus?status=available"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.exception("Failed to fetch pets from external Petstore API")
            raise e


async def process_entity_job(job_id: str, data: Dict[str, Any]):
    try:
        action = data.get("action")
        payload = data.get("data", {})

        if action == "fetch_all":
            pets = await fetch_all_pets_from_petstore()
            # Cache pets by id
            for pet in pets:
                pet_cache[str(pet.get("id"))] = pet
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = pets

        elif action == "fetch_by_type":
            pet_type = payload.get("type")
            if not pet_type:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = "Missing 'type' in data"
                return
            pets = await fetch_all_pets_from_petstore()
            filtered = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            for pet in filtered:
                pet_cache[str(pet.get("id"))] = pet
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = filtered

        elif action == "add_pet":
            # TODO: No external API supports POST add pet in the petstore free API
            # We mock adding pet to cache with generated id
            new_id = str(max([int(i) for i in pet_cache.keys()] + [0]) + 1)
            new_pet = payload.copy()
            new_pet["id"] = int(new_id)
            pet_cache[new_id] = new_pet
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = new_pet

        elif action == "update_pet":
            pet_id = str(payload.get("id"))
            if not pet_id or pet_id not in pet_cache:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = f"Pet id {pet_id} not found in cache"
                return
            pet_cache[pet_id].update(payload)
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = pet_cache[pet_id]

        elif action == "delete_pet":
            pet_id = str(payload.get("id"))
            if not pet_id or pet_id not in pet_cache:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = f"Pet id {pet_id} not found in cache"
                return
            deleted_pet = pet_cache.pop(pet_id)
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = deleted_pet

        else:
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["result"] = f"Unsupported action: {action}"

    except Exception as e:
        logger.exception("Error processing entity job")
        entity_jobs[job_id]["status"] = "error"
        entity_jobs[job_id]["result"] = str(e)


@app.route("/pets/query", methods=["POST"])
async def pets_query():
    data = await request.get_json(force=True)
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "result": None,
    }
    # Fire and forget processing
    asyncio.create_task(process_entity_job(job_id, data))
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/pets", methods=["GET"])
async def list_pets():
    # Return cached pets list
    pets_list = list(pet_cache.values())
    return jsonify(pets_list)


@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = pet_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/job_status/<job_id>", methods=["GET"])
async def get_job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        # Needed for proper asyncio event loop on Windows with Quart
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
