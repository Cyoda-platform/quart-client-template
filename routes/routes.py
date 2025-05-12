from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

entity_jobs: Dict[str, Dict[str, Any]] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
ENTITY_NAME = "pet"

@dataclass
class PetSyncFilter:
    type: Optional[str] = None
    status: Optional[str] = None

async def fetch_pets_from_petstore(pet_type: Optional[str] = None, status: Optional[str] = None) -> Dict[int, Dict[str, Any]]:
    params = {}
    if status:
        params["status"] = status
    else:
        params["status"] = "available"

    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
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

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Set default description if missing
    if not entity.get("description"):
        entity["description"] = "No description provided."

    # Add timestamp when processed
    entity["processedAt"] = datetime.utcnow().isoformat()

    # Add supplementary pet_metadata entity asynchronously
    pet_metadata = {
        "pet_id": entity.get("id"),
        "info": f"Metadata for pet {entity.get('name')}",
        "createdAt": datetime.utcnow().isoformat(),
    }

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_metadata",  # different entity model
            entity_version=ENTITY_VERSION,
            entity=pet_metadata,
            workflow=None,
        )
    except Exception as e:
        logger.warning(f"Failed to add supplementary pet_metadata entity: {e}")

    return entity

async def process_pet_sync(job_id: str, filter_params: Dict[str, Any]):
    try:
        entity_jobs[job_id]["status"] = "processing"
        pets = await fetch_pets_from_petstore(
            pet_type=filter_params.get("type"),
            status=filter_params.get("status"),
        )

        add_tasks = []
        for pet_id, pet in pets.items():
            pet_data = {
                "id": pet_id,
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "description": pet.get("description", ""),
                "age": None,
            }
            add_tasks.append(
                entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=ENTITY_NAME,
                    entity_version=ENTITY_VERSION,
                    entity=pet_data
                )
            )

        await asyncio.gather(*add_tasks)

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["count"] = len(pets)
        logger.info(f"Pet sync completed successfully: {len(pets)} pets loaded")
    except Exception as e:
        logger.exception(f"Error in pet sync processing: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

@app.route("/pets/sync", methods=["POST"])
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
    try:
        pets_list = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets_list)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

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