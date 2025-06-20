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

# In-memory local cache to simulate persistence (no global keyword, use app.state)
# Structure:
# app.state.pets_fetched: List[Dict] - raw fetched pets from external API
# app.state.pets_filtered: List[Dict] - filtered pets after business logic
# app.state.entity_jobs: Dict[str, Dict] - job statuses for async processing

app.state.pets_fetched: List[Dict] = []
app.state.pets_filtered: List[Dict] = []
app.state.entity_jobs: Dict[str, Dict] = {}


# External Petstore API base URL (Swagger Petstore example)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Helper: generate IDs for jobs (simple incremental int as str)
_job_counter = 0


def get_next_job_id() -> str:
    global _job_counter
    _job_counter += 1
    return str(_job_counter)


async def fetch_pets_from_petstore(
    pet_type: Optional[str], status: Optional[str], limit: Optional[int]
) -> List[Dict]:
    """
    Fetch pets from external Petstore API.
    pet_type corresponds to "category.name" in Petstore API (simulate with tag).
    status corresponds to pet status (available, pending, sold).
    Limit limits number of pets returned.
    """
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    # Petstore API accepts status param as CSV string, we will pass one or multiple if wanted.
    # For pet_type filtering, Petstore API does not provide direct category filter on this endpoint,
    # so we will filter locally after fetching.

    params = {}
    if status:
        params["status"] = status  # e.g. "available"
    else:
        # If no status provided, default to 'available' to avoid too large data
        params["status"] = "available"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore API: {e}")
        pets = []

    # Filter by pet_type locally (Petstore pets have 'category': {id, name} or None)
    if pet_type:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]

    if limit:
        pets = pets[:limit]

    # Normalize pets data to our app format, add "fun_category" placeholder None
    normalized_pets = []
    for pet in pets:
        normalized_pets.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name") if pet.get("category") else "unknown",
                "age": None,  # Petstore API does not provide age, will mock below
                "status": pet.get("status"),
                "fun_category": None,
            }
        )

    # TODO: Since Petstore API lacks age, mock random ages 1-10
    import random

    for pet in normalized_pets:
        pet["age"] = random.randint(1, 10)

    return normalized_pets


async def apply_filter_logic(
    pets: List[Dict],
    min_age: Optional[int],
    max_age: Optional[int],
    fun_category: Optional[str],
) -> List[Dict]:
    """
    Apply business logic filters on pets and assign fun_category if requested.
    fun_category can be 'playful' (age <= 3), 'sleepy' (age >= 7), or None.
    """
    filtered = []
    for pet in pets:
        age = pet.get("age")
        if min_age is not None and (age is None or age < min_age):
            continue
        if max_age is not None and (age is None or age > max_age):
            continue
        pet_copy = pet.copy()
        # Assign fun_category based on input or logic
        if fun_category:
            pet_copy["fun_category"] = fun_category
        else:
            # Auto assign by age for fun categories
            if age is not None:
                if age <= 3:
                    pet_copy["fun_category"] = "playful"
                elif age >= 7:
                    pet_copy["fun_category"] = "sleepy"
                else:
                    pet_copy["fun_category"] = "neutral"
            else:
                pet_copy["fun_category"] = "unknown"
        filtered.append(pet_copy)
    return filtered


async def process_fetch_job(job_id: str, data: dict):
    try:
        pets = await fetch_pets_from_petstore(data.get("type"), data.get("status"), data.get("limit"))
        # Update pets_fetched and pets_filtered cache atomically
        app.state.pets_fetched = pets
        app.state.pets_filtered = pets  # Initially filtered = fetched
        app.state.entity_jobs[job_id]["status"] = "completed"
        app.state.entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        app.state.entity_jobs[job_id]["result_count"] = len(pets)
        logger.info(f"Fetch job {job_id} completed with {len(pets)} pets.")
    except Exception as e:
        logger.exception(e)
        app.state.entity_jobs[job_id]["status"] = "failed"
        app.state.entity_jobs[job_id]["error"] = str(e)


async def process_filter_job(job_id: str, data: dict):
    try:
        filtered = await apply_filter_logic(
            app.state.pets_fetched,
            data.get("min_age"),
            data.get("max_age"),
            data.get("fun_category"),
        )
        app.state.pets_filtered = filtered
        app.state.entity_jobs[job_id]["status"] = "completed"
        app.state.entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        app.state.entity_jobs[job_id]["result_count"] = len(filtered)
        logger.info(f"Filter job {job_id} completed with {len(filtered)} pets.")
    except Exception as e:
        logger.exception(e)
        app.state.entity_jobs[job_id]["status"] = "failed"
        app.state.entity_jobs[job_id]["error"] = str(e)


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    job_id = get_next_job_id()
    app.state.entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget processing
    asyncio.create_task(process_fetch_job(job_id, data))
    return jsonify({"message": f"Fetch job started with id {job_id}", "job_id": job_id}), 202


@app.route("/pets/filter", methods=["POST"])
async def pets_filter():
    data = await request.get_json(force=True)
    job_id = get_next_job_id()
    app.state.entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_filter_job(job_id, data))
    return jsonify({"message": f"Filter job started with id {job_id}", "job_id": job_id}), 202


@app.route("/pets", methods=["GET"])
async def pets_get():
    # Return the currently filtered pets list
    return jsonify(app.state.pets_filtered)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_get(pet_id: int):
    pet = next((p for p in app.state.pets_filtered if p["id"] == pet_id), None)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/jobs/<job_id>", methods=["GET"])
async def job_status(job_id: str):
    job = app.state.entity_jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys

    # Enable debug level logging to stdout
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
