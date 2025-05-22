```python
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache for pets data.
# Structure: { pet_id: pet_data_dict }
pets_cache: Dict[int, Dict[str, Any]] = {}

# In-memory job tracking for fetch jobs: job_id -> status/info
entity_job: Dict[str, Dict[str, Any]] = {}

# Petstore base URL (Swagger Petstore)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility to generate simple unique job IDs (datetime-based)
def gen_job_id() -> str:
    return datetime.utcnow().isoformat(timespec='milliseconds').replace(":", "-")


async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch pets from Petstore API filtered by type and status."""
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    # Petstore API supports filtering by status only, not by type.
    # We'll fetch by status and then filter by type locally.
    # If no status specified, default to 'available' (common case).
    status_query = status if status else "available"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params={"status": status_query})
            r.raise_for_status()
            pets = r.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise

    # Filter by type locally if requested:
    if type_:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
    return pets


async def process_entity(job_id: str, type_: Optional[str], status: Optional[str]) -> None:
    """Background task to fetch, process, and cache pet data."""
    try:
        pets = await fetch_pets_from_petstore(type_, status)
        # Normalize and cache pets by their 'id'
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id is not None:
                # Add a simple description field for fun (TODO real descriptions)
                pet.setdefault("description", f"A lovely {pet.get('category', {}).get('name', 'pet')}.")
                pets_cache[pet_id] = pet
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["count"] = len(pets)
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed: {len(pets)} pets cached.")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed.")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Body: { "type": str (optional), "status": str (optional) }
    Fetches pets from Petstore external API, caches processed data.
    """
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")

    job_id = gen_job_id()
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "type": type_,
        "status_filter": status,
    }
    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id, type_, status))

    return jsonify({
        "message": "Pets data fetch started.",
        "job_id": job_id,
    })


@app.route("/pets", methods=["GET"])
async def pets_list():
    """
    GET /pets
    Query params: type (optional), status (optional)
    Returns cached pets filtered by query params from local cache.
    """
    type_filter = request.args.get("type")
    status_filter = request.args.get("status")

    def pet_matches(pet: Dict[str, Any]) -> bool:
        # Filter by type (category.name)
        if type_filter:
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type != type_filter.lower():
                return False
        # Filter by status
        if status_filter:
            pet_status = pet.get("status", "").lower()
            if pet_status != status_filter.lower():
                return False
        return True

    filtered_pets = [pet for pet in pets_cache.values() if pet_matches(pet)]

    # Respond with expected minimal fields
    response = []
    for pet in filtered_pets:
        response.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag] if pet.get("tags") else [],
            "photoUrls": pet.get("photoUrls", []),
        })

    return jsonify(response)


@app.route("/pets/recommend", methods=["POST"])
async def pets_recommend():
    """
    POST /pets/recommend
    Body: { "preferredType": str (optional), "maxResults": int (optional, default 3) }
    Return fun pet recommendations from cached data.
    """
    data = await request.get_json(force=True)
    preferred_type = data.get("preferredType")
    max_results = data.get("maxResults", 3)

    # Filter cached pets by preferred type if given
    candidates = []
    for pet in pets_cache.values():
        if preferred_type:
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type != preferred_type.lower():
                continue
        candidates.append(pet)

    # If no candidates found and preferred_type was given, fallback to all pets
    if preferred_type and not candidates:
        candidates = list(pets_cache.values())

    # Pick up to max_results pets (random order)
    # TODO: For real randomness, import random and shuffle. Here simple slice.
    recommended = candidates[:max_results]

    # Add a funFact field (placeholder)
    response = []
    for pet in recommended:
        response.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "funFact": f"{pet.get('name')} loves to play and cuddle! 😸",  # TODO: Replace with real fun facts
        })

    return jsonify(response)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    """
    GET /pets/{petId}
    Return detailed info about a single pet from cache.
    """
    pet = pets_cache.get(pet_id)
    if not pet:
        abort(404, description=f"Pet with id {pet_id} not found in cache.")

    response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag] if pet.get("tags") else [],
        "photoUrls": pet.get("photoUrls", []),
        "description": pet.get("description"),
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
