```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" mocks
pets_db: Dict[str, Dict[str, Any]] = {}
entity_job: Dict[str, Dict[str, Any]] = {}

# Petstore API base URL (public Swagger Petstore)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# For random pet facts - using a public API for animal facts
# TODO: If you want other sources, swap this URL
RANDOM_PET_FACTS_URL = "https://some-random-api.ml/facts/cat"

import uuid


async def fetch_pet_from_petstore(pet_id: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
            return pet
        except httpx.HTTPStatusError as e:
            logger.warning(f"Petstore API returned error for pet_id={pet_id}: {e}")
            return None
        except Exception as e:
            logger.exception(e)
            return None


async def search_pets_from_petstore(
    category: Optional[str], status: Optional[str], tags: Optional[List[str]]
) -> List[Dict[str, Any]]:
    # Petstore API supports status filtering, tags is not official but we filter manually
    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            params = {}
            if status:
                params["status"] = status
            else:
                params["status"] = "available,pending,sold"

            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()

            # Filter by category and tags locally
            def matches(p):
                if category and (p.get("category", {}).get("name", "").lower() != category.lower()):
                    return False
                if tags:
                    pet_tags = [t["name"].lower() for t in p.get("tags", [])]
                    if not all(tag.lower() in pet_tags for tag in tags):
                        return False
                return True

            filtered = [p for p in pets if matches(p)]
            return filtered
        except Exception as e:
            logger.exception(e)
            return []


async def get_random_pet_fact() -> str:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(RANDOM_PET_FACTS_URL)
            r.raise_for_status()
            data = r.json()
            fact = data.get("fact")
            if not fact:
                fact = "Cats are mysterious and wonderful creatures!"
            return fact
        except Exception as e:
            logger.warning(f"Failed to fetch random pet fact: {e}")
            return "Cats are mysterious and wonderful creatures!"


async def process_entity(job_id: str, data: Dict[str, Any]):
    try:
        action = data.get("action")
        pet_data = data.get("pet", {})
        result_pet = None

        if action == "fetch":
            pet_id = str(pet_data.get("id", ""))
            if not pet_id:
                entity_job[job_id]["status"] = "error"
                return
            pet = await fetch_pet_from_petstore(pet_id)
            if pet:
                pets_db[pet_id] = pet
                result_pet = pet
            else:
                entity_job[job_id]["status"] = "not_found"
                return

        elif action == "add":
            # Generate ID if missing
            pet_id = pet_data.get("id") or str(uuid.uuid4())
            pet_data["id"] = pet_id
            pets_db[pet_id] = pet_data
            result_pet = pet_data

            # TODO: Optionally sync with Petstore API (not in prototype)

        elif action == "update":
            pet_id = pet_data.get("id")
            if not pet_id or pet_id not in pets_db:
                entity_job[job_id]["status"] = "error"
                return
            pets_db[pet_id].update(pet_data)
            result_pet = pets_db[pet_id]

            # TODO: Optionally sync update with Petstore API (not in prototype)

        else:
            entity_job[job_id]["status"] = "error"
            return

        entity_job[job_id]["status"] = "done"
        entity_job[job_id]["result"] = result_pet

    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "error"


@app.route("/pets", methods=["POST"])
async def pets_post():
    data = await request.get_json()
    job_id = str(uuid.uuid4())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/pets/job-status/<job_id>", methods=["GET"])
async def job_status(job_id):
    job = entity_job.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "done":
        return jsonify({"status": "done", "result": job.get("result")})
    else:
        return jsonify({"status": job["status"]})


@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = pets_db.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    data = await request.get_json()
    category = data.get("category")
    status = data.get("status")
    tags = data.get("tags")

    pets = await search_pets_from_petstore(category, status, tags)
    return jsonify({"pets": pets})


@app.route("/pets/random-fact", methods=["GET"])
async def random_fact():
    fact = await get_random_pet_fact()
    return jsonify({"fact": fact})


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```