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

# In-memory "storage" for pets data and favorites – async safe using asyncio.Lock
pets_data = []
pets_data_lock = asyncio.Lock()

favorites: Dict[str, set] = {}  # userId -> set of petIds
favorites_lock = asyncio.Lock()

# In-memory job tracker for fetch requests
entity_job: Dict[str, Dict[str, Any]] = {}
entity_job_lock = asyncio.Lock()

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(filter_params: Dict[str, Any]) -> list:
    """
    Fetch pet data from Petstore API according to filter params.
    Note: Petstore API has /pet/findByStatus endpoint that supports status filter.
    No direct filtering by type available, so filtering by type will be done locally.
    """
    status = filter_params.get("status", "available")
    limit = filter_params.get("limit", 50)

    async with httpx.AsyncClient() as client:
        try:
            # Petstore supports multiple comma separated statuses, we take one for simplicity
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(e)
            return []

    # Filter by type locally if requested (type corresponds to pet.category.name)
    pet_type = filter_params.get("type")
    if pet_type:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]

    # Sort if requested
    sort_field = filter_params.get("sort")
    if sort_field:
        def sort_key(p):
            # Support sorting by name, status, type(category.name)
            if sort_field == "name":
                return p.get("name", "")
            elif sort_field == "status":
                return p.get("status", "")
            elif sort_field == "type":
                return p.get("category", {}).get("name", "")
            return ""
        pets = sorted(pets, key=sort_key)

    # Limit results
    pets = pets[:limit]

    return pets


async def process_fetch_job(job_id: str, filter_params: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_petstore(filter_params)
        async with pets_data_lock:
            pets_data.clear()
            pets_data.extend(pets)
        async with entity_job_lock:
            entity_job[job_id]["status"] = "completed"
            entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
            entity_job[job_id]["count"] = len(pets)
        logger.info(f"Fetch job {job_id} completed with {len(pets)} pets.")
    except Exception as e:
        async with entity_job_lock:
            entity_job[job_id]["status"] = "failed"
            entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
            entity_job[job_id]["error"] = str(e)
        logger.exception(e)


@app.route('/purrfect-pets/fetch', methods=['POST'])
async def fetch_pets():
    """
    POST /purrfect-pets/fetch
    Request JSON:
    {
        "filter": {
            "status": "available|pending|sold",
            "type": "cat|dog|bird|..."
        },
        "sort": "name|status|type",
        "limit": 50
    }
    Response:
    {
        "message": "Data fetched and processed successfully",
        "count": 42,
        "jobId": "some-uuid"
    }
    """
    data = await request.get_json(force=True)
    filter_params = data.get("filter", {})
    sort = data.get("sort")
    limit = data.get("limit")

    # Validate minimal input for demo - no strict validation for prototype
    filter_params = filter_params if isinstance(filter_params, dict) else {}

    # Compose job id
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    async with entity_job_lock:
        entity_job[job_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
        }

    # Fire and forget processing task
    asyncio.create_task(process_fetch_job(job_id, {**filter_params, "sort": sort, "limit": limit}))

    return jsonify({
        "message": "Fetch job started",
        "jobId": job_id,
    })


@app.route('/purrfect-pets/list', methods=['GET'])
async def list_pets():
    """
    GET /purrfect-pets/list
    Response: list of pets with minimal info
    """
    async with pets_data_lock:
        # Return only minimal info per pet
        pets_summary = [{
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
        } for pet in pets_data]

    return jsonify(pets_summary)


@app.route('/purrfect-pets/details/<int:pet_id>', methods=['GET'])
async def pet_details(pet_id: int):
    """
    GET /purrfect-pets/details/{petId}
    Response: full details for the pet or 404
    """
    async with pets_data_lock:
        pet = next((p for p in pets_data if p.get("id") == pet_id), None)

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    # Compose detailed response, adding description and tags fields (mocked since Petstore API does not provide description)
    response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        "description": f"A lovely {pet.get('category', {}).get('name', 'pet')} named {pet.get('name')}.",  # TODO: Use real descriptions if available
    }
    return jsonify(response)


@app.route('/purrfect-pets/favorite', methods=['POST'])
async def favorite_pet():
    """
    POST /purrfect-pets/favorite
    Request JSON:
    {
        "petId": 1,
        "userId": "user123"
    }
    Response:
    {
        "message": "Pet added to favorites"
    }
    """
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    user_id = data.get("userId")

    if pet_id is None or user_id is None:
        return jsonify({"error": "petId and userId are required"}), 400

    # Check pet exists
    async with pets_data_lock:
        exists = any(p.get("id") == pet_id for p in pets_data)

    if not exists:
        return jsonify({"error": "Pet not found"}), 404

    async with favorites_lock:
        user_favs = favorites.setdefault(user_id, set())
        user_favs.add(pet_id)

    return jsonify({"message": "Pet added to favorites"})


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
