from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

pets_cache: Dict[int, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


@dataclass
class PetSyncFilter:
    type: Optional[str] = None
    status: Optional[str] = None


async def fetch_pets_from_petstore(
    pet_type: Optional[str] = None, status: Optional[str] = None
) -> Dict[int, Dict[str, Any]]:
    params = {}
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            if not status:
                params["status"] = "available"
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets_list = resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch pets from Petstore: {e}")
            return {}

    if pet_type:
        filtered = {
            pet["id"]: pet
            for pet in pets_list
            if pet.get("category") and pet["category"].get("name") == pet_type
        }
    else:
        filtered = {pet["id"]: pet for pet in pets_list}

    return filtered


async def process_pet_sync(job_id: str, filter_params: Dict[str, Any]):
    try:
        entity_jobs[job_id]["status"] = "processing"
        pets = await fetch_pets_from_petstore(
            pet_type=filter_params.get("type"), status=filter_params.get("status")
        )

        pets_cache.clear()
        for pet_id, pet in pets.items():
            pets_cache[pet_id] = {
                "id": pet_id,
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "description": pet.get("description", ""),
                "age": None,  # TODO: Petstore API doesn't provide age; could mock or omit
            }

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["count"] = len(pets_cache)
        logger.info(f"Pet sync completed successfully: {len(pets_cache)} pets loaded")
    except Exception as e:
        logger.exception(f"Error in pet sync processing: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)


@app.route("/pets/sync", methods=["POST"])
# POST validation must come after route decorator (issue workaround)
@validate_request(PetSyncFilter)
async def pets_sync(data: PetSyncFilter):
    try:
        filter_params = data.__dict__ if data else {}

        job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        entity_jobs[job_id] = {
            "status": "pending",
            "requestedAt": datetime.utcnow().isoformat(),
            "filter": filter_params,
        }

        asyncio.create_task(process_pet_sync(job_id, filter_params))

        return jsonify(
            {
                "message": "Pet synchronization started",
                "jobId": job_id,
                "filter": filter_params,
            }
        ), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Invalid request"}), 400


@app.route("/pets", methods=["GET"])
async def get_pets():
    pets_list = list(pets_cache.values())
    return jsonify(pets_list)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/fun/fact", methods=["GET"])
async def get_random_pet_fact():
    facts = [
        "Cats sleep for 70% of their lives.",
        "Dogs have three eyelids.",
        "Rabbits can't vomit.",
        "Parrots will selflessly help each other.",
        "Goldfish can recognize faces.",
    ]
    import random

    fact = random.choice(facts)
    return jsonify({"fact": fact})


@app.route("/pets/sync/status/<job_id>", methods=["GET"])
async def get_sync_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
