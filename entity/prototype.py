import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class PetQuery:
    type: Optional[str]
    status: Optional[str]

@dataclass
class FavoritePet:
    petId: int

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
    statuses = [status_filter] if status_filter else ["available"]
    pets: List[dict] = []
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
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets


async def trigger_event_workflow(event_type: str, payload: dict):
    job_id = f"{event_type}_{datetime.utcnow().isoformat()}"
    async with entity_jobs_lock:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "payload": payload}
    logger.info(f"Event triggered: {event_type}, job id: {job_id}")
    asyncio.create_task(process_event_job(job_id))


async def process_event_job(job_id: str):
    try:
        await asyncio.sleep(0.5)
        async with entity_jobs_lock:
            if job_id in entity_jobs:
                entity_jobs[job_id]["status"] = "done"
                logger.info(f"Event job {job_id} done.")
    except Exception as e:
        logger.exception(f"Error processing event job {job_id}: {e}")

@app.route("/pets/query", methods=["POST"])
# workaround: validation must be last decorator for POST due to quart-schema defect
@validate_request(PetQuery)
async def pets_query(data: PetQuery):
    try:
        pets = await fetch_pets_from_petstore(data.type, data.status)
        async with cache_lock:
            pets_cache.clear()
            for pet in pets:
                pid = pet.get("id")
                if pid is not None:
                    pets_cache[pid] = pet
        await trigger_event_workflow("pet_query", {"type": data.type, "status": data.status, "resultCount": len(pets)})
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception("Error in /pets/query")
        return jsonify({"error": "Failed to query pets"}), 500

@app.route("/pets", methods=["GET"])
async def pets_get():
    try:
        async with cache_lock:
            pets = list(pets_cache.values())
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception("Error in /pets GET")
        return jsonify({"error": "Failed to get cached pets"}), 500

@app.route("/pets/favorite", methods=["POST"])
# workaround: validation must be last decorator for POST due to quart-schema defect
@validate_request(FavoritePet)
async def pets_favorite(data: FavoritePet):
    try:
        pet_id = data.petId
        async with cache_lock:
            pet = pets_cache.get(pet_id)
        if pet is None:
            return jsonify({"error": "Pet not found in cache"}), 404
        async with cache_lock:
            favorites_cache[pet_id] = pet
        await trigger_event_workflow("pet_favorite", {"petId": pet_id})
        return jsonify({"message": "Pet marked as favorite", "petId": pet_id})
    except Exception as e:
        logger.exception("Error in /pets/favorite")
        return jsonify({"error": "Failed to mark pet as favorite"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)