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

# In-memory async-safe cache for pets and jobs
pets_cache: Dict[int, dict] = {}
entity_jobs: Dict[str, dict] = {}

# Petstore API base URL
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Simple ID generator for new pets (incremental from max cached ID)
def next_pet_id() -> int:
    if pets_cache:
        return max(pets_cache.keys()) + 1
    return 1000  # Start from 1000 to avoid overlap with petstore IDs


async def fetch_pets_from_petstore(filter_status: Optional[str], filter_category: Optional[str]) -> list:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # Petstore API: GET /pet/findByStatus?status=available
            # But we do external calls only inside POST, so we do this here
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {}
            if filter_status:
                params["status"] = filter_status
            else:
                params["status"] = "available"  # default filter if none provided

            response = await client.get(url, params=params)
            response.raise_for_status()
            pets = response.json()

            # Optional filtering by category (Petstore uses 'category' with 'id' and 'name')
            if filter_category:
                filtered = []
                for pet in pets:
                    cat = pet.get("category")
                    if cat and cat.get("name", "").lower() == filter_category.lower():
                        filtered.append(pet)
                return filtered
            return pets

        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            return []


async def process_fetch_pets_job(job_id: str, filter_status: Optional[str], filter_category: Optional[str]):
    try:
        pets = await fetch_pets_from_petstore(filter_status, filter_category)
        # Normalize and store in cache (only keep needed fields)
        pets_cache.clear()
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id is None:
                continue
            pets_cache[pet_id] = {
                "id": pet_id,
                "name": pet.get("name"),
                "category": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", []) if tag.get("name")]
            }
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["pets_count"] = len(pets_cache)
        logger.info(f"Fetch pets job {job_id} completed, {len(pets_cache)} pets cached.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Fetch pets job {job_id} failed.")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    filter_ = data.get("filter", {})
    status = filter_.get("status")
    category = filter_.get("category")

    job_id = f"fetch_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }

    # Fire and forget processing task
    asyncio.create_task(process_fetch_pets_job(job_id, status, category))

    return jsonify({
        "message": "Data fetch initiated",
        "job_id": job_id
    })


@app.route("/pets", methods=["GET"])
async def list_pets():
    # Return list of cached pets
    return jsonify(list(pets_cache.values()))


@app.route("/pets/add", methods=["POST"])
async def add_pet():
    data = await request.get_json(force=True)
    name = data.get("name")
    category = data.get("category")
    status_ = data.get("status")
    tags = data.get("tags", [])

    if not name or not category or not status_:
        return jsonify({"message": "Missing required pet fields (name, category, status)"}), 400

    pet_id = next_pet_id()
    pets_cache[pet_id] = {
        "id": pet_id,
        "name": name,
        "category": category,
        "status": status_,
        "tags": tags,
    }

    logger.info(f"Added new pet with ID {pet_id}")

    return jsonify({
        "message": "Pet added successfully",
        "pet_id": pet_id
    })


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/update/<int:pet_id>", methods=["POST"])
async def update_pet(pet_id):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404

    data = await request.get_json(force=True)

    # Update fields if provided
    name = data.get("name")
    category = data.get("category")
    status_ = data.get("status")
    tags = data.get("tags")

    if name is not None:
        pet["name"] = name
    if category is not None:
        pet["category"] = category
    if status_ is not None:
        pet["status"] = status_
    if tags is not None:
        pet["tags"] = tags

    pets_cache[pet_id] = pet

    logger.info(f"Updated pet with ID {pet_id}")

    return jsonify({"message": "Pet updated successfully"})


if __name__ == '__main__':
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
