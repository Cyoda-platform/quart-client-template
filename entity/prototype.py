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

# In-memory caches (asyncio-safe by design of Quart single-threaded event loop)
pets_cache: List[Dict] = []  # Stores fetched & enriched pets
favorites_cache: List[Dict] = []  # Stores favorite pets (by full pet dict)

# Entity job status tracking for fetch operations
entity_jobs: Dict[str, Dict] = {}


async def fetch_petstore_data(pet_type: Optional[str], status: Optional[str]) -> List[Dict]:
    """
    Fetch pets data from the Petstore API (https://petstore.swagger.io/v2/pet/findByStatus).
    Since Petstore API does not support filtering by type, we do it client-side.
    """
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    statuses = ["available", "pending", "sold"]

    # If status provided, validate it, else default to all statuses
    if status and status.lower() in statuses:
        query_statuses = [status.lower()]
    else:
        query_statuses = statuses

    pets = []
    async with httpx.AsyncClient() as client:
        for s in query_statuses:
            try:
                resp = await client.get(url, params={"status": s}, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                pets.extend(data if isinstance(data, list) else [])
            except Exception as e:
                logger.exception(f"Error fetching pets for status={s}: {e}")

    # Filter by pet_type if provided (Petstore API pets have 'category' with 'name')
    if pet_type:
        pet_type_lower = pet_type.lower()
        filtered = []
        for pet in pets:
            category = pet.get("category")
            if category and isinstance(category, dict):
                cat_name = category.get("name", "").lower()
                if cat_name == pet_type_lower:
                    filtered.append(pet)
        pets = filtered

    return pets


def enrich_pet_description(pet: Dict) -> str:
    """
    Add a playful/fun description based on pet type or status.
    This is a simple example enrichment.
    """
    pet_type = pet.get("category", {}).get("name", "pet").lower()
    status = pet.get("status", "unknown").lower()
    name = pet.get("name", "This pet")

    descriptions = {
        "dog": f"{name} is a loyal doggie who loves belly rubs!",
        "cat": f"{name} is a curious cat with nine lives and endless naps.",
        "bird": f"{name} sings sweet melodies all day long.",
    }
    default_desc = f"{name} is a wonderful {pet_type} currently {status}."

    return descriptions.get(pet_type, default_desc)


async def process_fetch_job(job_id: str, pet_type: Optional[str], status: Optional[str]):
    """
    Background task to fetch, enrich, and store pets data.
    """
    try:
        pets_raw = await fetch_petstore_data(pet_type, status)
        pets_enriched = []
        for pet in pets_raw:
            pet_copy = pet.copy()
            pet_copy["description"] = enrich_pet_description(pet)
            pets_enriched.append(pet_copy)

        # Store to cache atomically by replacing the global list
        # Since Quart runs single-threaded event loop, this is safe.
        global pets_cache
        pets_cache.clear()
        pets_cache.extend(pets_enriched)

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["count"] = len(pets_enriched)
        logger.info(f"Fetch job {job_id} completed with {len(pets_enriched)} pets.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Fetch job {job_id} failed.")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Request JSON (optional):
    {
        "type": "cat" | "dog" | ...
        "status": "available" | "pending" | "sold"
    }
    Response:
    {
        "message": "...",
        "count": number
    }
    """
    data = await request.get_json(force=True, silent=True) or {}
    pet_type = data.get("type")
    status = data.get("status")

    job_id = datetime.utcnow().isoformat()  # simple unique job id
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": job_id,
        "type": pet_type,
        "status_filter": status,
    }

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_job(job_id, pet_type, status))

    # Immediately respond (prototype UX)
    return jsonify({
        "message": "Pets data fetch started",
        "job_id": job_id,
        "status": "processing"
    })


@app.route("/pets", methods=["GET"])
async def get_all_pets():
    """
    GET /pets
    Returns the list of cached pets with descriptions.
    """
    return jsonify(pets_cache)


@app.route("/favorites/add", methods=["POST"])
async def add_favorite():
    """
    POST /favorites/add
    Request JSON:
    {
        "pet_id": "string"
    }
    Response:
    {
        "message": "Pet added to favorites"
    }
    """
    data = await request.get_json(force=True, silent=True) or {}
    pet_id = data.get("pet_id")
    if not pet_id:
        return jsonify({"message": "pet_id is required"}), 400

    # Find pet by id in cached pets
    pet = next((p for p in pets_cache if str(p.get("id")) == str(pet_id)), None)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404

    # Check if already favorite
    if any(str(fav.get("id")) == str(pet_id) for fav in favorites_cache):
        return jsonify({"message": "Pet already in favorites"}), 200

    favorites_cache.append(pet)
    logger.info(f"Pet {pet_id} added to favorites.")
    return jsonify({"message": "Pet added to favorites"})


@app.route("/favorites", methods=["GET"])
async def get_favorites():
    """
    GET /favorites
    Returns the list of favorite pets.
    """
    return jsonify(favorites_cache)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```