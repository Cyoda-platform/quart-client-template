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

# Local in-memory cache / "database" for pets: pet_id -> pet_data
pets_cache: Dict[int, Dict[str, Any]] = {}
next_pet_id = 1000  # for created pets locally

# Entity job tracking for async processing (e.g. external API calls)
entity_job: Dict[str, Dict[str, Any]] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fire external Petstore API call to fetch pets (simulate filtering client-side because Petstore API is limited).
    TODO: Improve filtering logic or use real Petstore API filter if available.
    """
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    status = filters.get("status", "available")
    params = {"status": status}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()

            # Apply additional filtering (type, name) client-side
            filtered = []
            pet_type = filters.get("type")
            name = filters.get("name")

            for pet in pets:
                if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
                    continue
                if name and name.lower() not in pet.get("name", "").lower():
                    continue
                filtered.append(pet)

            # Cache filtered pets internally (simulate)
            for pet in filtered:
                pets_cache[pet["id"]] = pet

            return {"pets": filtered}

    except Exception as e:
        logger.exception(e)
        return {"pets": []}


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    """
    Search pets with filters. Fetch data from Petstore API.
    """
    filters = await request.get_json()
    job_id = str(datetime.utcnow().timestamp())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget fetch
    async def process_search():
        result = await fetch_pets_from_petstore(filters)
        entity_job[job_id]["status"] = "done"
        entity_job[job_id]["result"] = result

    asyncio.create_task(process_search())

    # For prototype: Wait for task completion to return result (to simplify UX)
    # TODO: In real app use async job status system
    await asyncio.sleep(1)  # simulate minimal wait (replace with better sync in prod)
    result = entity_job[job_id].get("result", {"pets": []})
    return jsonify(result)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    """
    Retrieve pet details from internal cache.
    """
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets", methods=["POST"])
async def create_pet():
    """
    Add a new pet to internal cache. Simulated creation.
    """
    global next_pet_id
    data = await request.get_json()
    next_pet_id += 1
    pet_id = next_pet_id

    pet = {
        "id": pet_id,
        "name": data.get("name", ""),
        "type": data.get("type", ""),
        "status": data.get("status", "available"),
        "category": data.get("category", "pets"),
        "photoUrls": data.get("photoUrls", []),
    }
    pets_cache[pet_id] = pet

    return jsonify({"id": pet_id, "message": "Pet created successfully"}), 201


@app.route("/pets/<int:pet_id>", methods=["POST"])
async def update_pet(pet_id: int):
    """
    Update pet details internally.
    """
    data = await request.get_json()
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    # Update allowed fields only
    for key in ["name", "type", "status", "category", "photoUrls"]:
        if key in data:
            pet[key] = data[key]

    pets_cache[pet_id] = pet
    return jsonify({"id": pet_id, "message": "Pet updated successfully"})


@app.route("/pets/<int:pet_id>/delete", methods=["POST"])
async def delete_pet(pet_id: int):
    """
    Delete pet from internal cache.
    """
    if pet_id not in pets_cache:
        return jsonify({"error": "Pet not found"}), 404

    del pets_cache[pet_id]
    return jsonify({"id": pet_id, "message": "Pet deleted successfully"})


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
