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

# Local in-memory caches (async safe usage via asyncio.Lock)
pets_cache: Dict[int, dict] = {}
favorites_cache: Dict[int, dict] = {}
cache_lock = asyncio.Lock()

# Simulated entity job store for event-driven workflow simulation
entity_jobs: Dict[str, dict] = {}
entity_jobs_lock = asyncio.Lock()

# External Petstore API base URL
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    type_filter: Optional[str] = None, status_filter: Optional[str] = None
) -> List[dict]:
    """
    Fetch pets from Petstore API by status.
    Petstore API supports filtering by status only for /pet/findByStatus.
    Filtering by type is done locally.

    Petstore API endpoints used:
    GET /pet/findByStatus?status=available,sold,pending

    TODO: Petstore API does not provide a direct filter by type, so type filtering is done locally.
    """

    statuses = []
    if status_filter:
        statuses = [status_filter]
    else:
        # Default to "available" if no status specified
        statuses = ["available"]

    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        for status in statuses:
            try:
                resp = await client.get(
                    f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status}
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
            except httpx.HTTPError as e:
                logger.exception(f"Failed to fetch pets by status '{status}': {e}")

    # Filter by type locally if requested
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]

    return pets


async def trigger_event_workflow(event_type: str, payload: dict):
    """
    Simulate event-driven workflow by logging and storing event job status.
    Fire and forget the processing task.
    """

    job_id = f"{event_type}_{datetime.utcnow().isoformat()}"
    async with entity_jobs_lock:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "payload": payload}
    logger.info(f"Event triggered: {event_type}, job id: {job_id}")
    # Fire and forget processing task
    asyncio.create_task(process_event_job(job_id))


async def process_event_job(job_id: str):
    """
    Simulated async event processing logic.
    Here we just wait a bit and then mark job done.
    """

    try:
        await asyncio.sleep(0.5)  # Simulate some processing delay
        async with entity_jobs_lock:
            if job_id in entity_jobs:
                entity_jobs[job_id]["status"] = "done"
                logger.info(f"Event job {job_id} done.")
    except Exception as e:
        logger.exception(f"Error processing event job {job_id}: {e}")


@app.route("/pets/query", methods=["POST"])
async def pets_query():
    """
    POST /pets/query
    Request JSON:
    {
        "type": "string",      # optional, e.g. "cat", "dog"
        "status": "string"     # optional, e.g. "available", "sold"
    }
    Response JSON:
    {
        "pets": [ ... pet objects ... ]
    }
    """
    try:
        data = await request.get_json()
        type_filter = data.get("type") if data else None
        status_filter = data.get("status") if data else None

        pets = await fetch_pets_from_petstore(type_filter, status_filter)

        # Cache pets (overwrite cache with latest query results)
        async with cache_lock:
            pets_cache.clear()
            for pet in pets:
                pet_id = pet.get("id")
                if pet_id is not None:
                    pets_cache[pet_id] = pet

        # Trigger query event workflow (fire & forget)
        await trigger_event_workflow("pet_query", {"type": type_filter, "status": status_filter, "resultCount": len(pets)})

        return jsonify({"pets": pets})

    except Exception as e:
        logger.exception("Error in /pets/query")
        return jsonify({"error": "Failed to query pets"}), 500


@app.route("/pets", methods=["GET"])
async def pets_get():
    """
    GET /pets
    Returns cached pets from last query.
    Response JSON:
    {
        "pets": [ ... pet objects ... ]
    }
    """
    try:
        async with cache_lock:
            pets = list(pets_cache.values())
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception("Error in /pets GET")
        return jsonify({"error": "Failed to get cached pets"}), 500


@app.route("/pets/favorite", methods=["POST"])
async def pets_favorite():
    """
    POST /pets/favorite
    Request JSON:
    {
        "petId": integer
    }
    Response JSON:
    {
        "message": "Pet marked as favorite",
        "petId": integer
    }
    """
    try:
        data = await request.get_json()
        pet_id = data.get("petId") if data else None
        if pet_id is None:
            return jsonify({"error": "petId is required"}), 400

        async with cache_lock:
            pet = pets_cache.get(pet_id)
        if pet is None:
            return jsonify({"error": "Pet not found in cache"}), 404

        async with cache_lock:
            favorites_cache[pet_id] = pet

        # Trigger favorite event workflow
        await trigger_event_workflow("pet_favorite", {"petId": pet_id})

        return jsonify({"message": "Pet marked as favorite", "petId": pet_id})

    except Exception as e:
        logger.exception("Error in /pets/favorite")
        return jsonify({"error": "Failed to mark pet as favorite"}), 500


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
