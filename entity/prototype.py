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

# In-memory cache for pets data keyed by "latest"
pets_cache: Dict[str, List[Dict]] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    type_: Optional[str] = None, status: Optional[str] = None
) -> List[Dict]:
    """
    Fetch pets from Petstore API filtered by type and status.
    Petstore API endpoint: /pet/findByStatus?status=available,sold,pending
    Note: type filtering will be done client-side as Petstore API doesn't support type filter.
    """
    statuses = []
    if status:
        # Petstore API expects one or multiple statuses comma separated
        # Support single status only for simplicity here
        statuses = [status]
    else:
        # Default to all statuses if none provided
        statuses = ["available", "pending", "sold"]

    pets: List[Dict] = []
    async with httpx.AsyncClient() as client:
        for s in statuses:
            try:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": s})
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
                else:
                    logger.warning(f"Unexpected data format from petstore: {data}")
            except Exception as e:
                logger.exception(f"Failed to fetch pets for status '{s}': {e}")

    if type_:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]

    return pets


async def process_fetch_pets_job(job_id: str, filters: Dict):
    try:
        pets = await fetch_pets_from_petstore(filters.get("type"), filters.get("status"))
        pets_cache["latest"] = pets
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"pets": pets}
        logger.info(f"Pet data fetch job {job_id} completed with {len(pets)} pets.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["result"] = {"error": str(e)}
        logger.exception(e)


async def process_pet_match_job(job_id: str, preferences: Dict):
    try:
        pets = pets_cache.get("latest", [])
        preferred_type = preferences.get("preferredType", "").lower()
        preferred_status = preferences.get("preferredStatus", "").lower()

        filtered = pets
        if preferred_type:
            filtered = [p for p in filtered if p.get("category", {}).get("name", "").lower() == preferred_type]
        if preferred_status:
            filtered = [p for p in filtered if p.get("status", "").lower() == preferred_status]

        matched_pet = filtered[0] if filtered else None

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"matchedPet": matched_pet}
        logger.info(f"Pet match job {job_id} completed. Matched pet: {matched_pet.get('name') if matched_pet else 'None'}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["result"] = {"error": str(e)}
        logger.exception(e)


entity_jobs: Dict[str, Dict] = {}


def create_job() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Body: { "type": <str>, "status": <str> }
    Triggers fetching pets from external Petstore API with optional filters.
    Returns job_id to get results later.
    """
    filters = await request.get_json(force=True) or {}
    job_id = create_job()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_pets_job(job_id, filters))
    return jsonify({"jobId": job_id, "status": "processing"}), 202


@app.route("/pets", methods=["GET"])
async def get_cached_pets():
    """
    GET /pets
    Returns the most recently fetched pet data from cache.
    """
    pets = pets_cache.get("latest")
    if pets is None:
        return jsonify({"pets": []})
    return jsonify({"pets": pets})


@app.route("/pets/match", methods=["POST"])
async def pet_match():
    """
    POST /pets/match
    Body: { "preferredType": <str>, "preferredStatus": <str> }
    Matches a pet from cached data based on user preferences.
    Returns job_id to get results later.
    """
    preferences = await request.get_json(force=True) or {}
    job_id = create_job()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_pet_match_job(job_id, preferences))
    return jsonify({"jobId": job_id, "status": "processing"}), 202


@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id):
    """
    GET /jobs/<job_id>
    Returns the status and result of an asynchronous job.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
