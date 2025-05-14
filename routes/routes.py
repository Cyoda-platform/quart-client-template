import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service, BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# Request schemas
@dataclass
class PetFetchRequest:
    filter: dict  # e.g. {"status": "available", "type": "dog"}

@dataclass
class FunFactRequest:
    type: Optional[str] = None

fun_facts_cache: List[str] = [
    "Cats sleep for 70% of their lives.",
    "Dogs have a sense of time and can miss you.",
    "Rabbits can see behind them without turning their heads.",
    "Guinea pigs communicate with purrs and squeaks.",
    "Parrots can live for over 80 years."
]

PET_ENTITY_NAME = "pet"
PET_FETCH_JOB_ENTITY_NAME = "pet_fetch_job"

# === Workflow functions ===

async def process_pet(entity: dict) -> dict:
    """
    Workflow for pet entity.
    Enrich pet with a fun fact before persistence.
    """
    import random
    # Defensive: Ensure entity is a dict and can be modified
    if not isinstance(entity, dict):
        return entity
    entity['funFact'] = random.choice(fun_facts_cache)
    return entity

async def process_pet_fetch_job(entity: dict) -> dict:
    """
    Workflow for pet_fetch_job entity.
    Fetch pets from external API with filters, then add pet entities.
    Update job entity status and metadata.
    """
    try:
        # Defensive: Ensure entity dict has 'filter'
        filter_data = entity.get("filter") if isinstance(entity, dict) else {}
        if not isinstance(filter_data, dict):
            filter_data = {}

        status = filter_data.get("status")
        pet_type = filter_data.get("type")

        async with httpx.AsyncClient(timeout=10) as client:
            params = {}
            if status:
                params["status"] = status
            resp = await client.get("https://petstore3.swagger.io/api/v3/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets = resp.json()
            if not isinstance(pets, list):
                pets = []

        # Filter pets by type if specified
        if pet_type:
            pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]

        count_added = 0
        # Add pet entities, passing the pet workflow
        for pet in pets:
            try:
                # Defensive: skip invalid pet objects
                if not isinstance(pet, dict):
                    continue
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=PET_ENTITY_NAME,
                    entity_version=ENTITY_VERSION,
                    entity=pet
                )
                count_added += 1
            except Exception as e:
                logger.exception(f"Failed to add pet entity: {e}")

        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["count"] = count_added
    except Exception as e:
        logger.exception(f"Failed processing pet fetch job: {e}")
        entity["status"] = "failed"
        entity["error"] = str(e)
    return entity

# === Endpoints ===

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)
async def fetch_pets(data: PetFetchRequest):
    """
    Create a pet_fetch_job entity.
    The workflow will fetch pets and add pet entities asynchronously.
    """
    job_entity = {
        "filter": data.filter if isinstance(data.filter, dict) else {},
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_FETCH_JOB_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=job_entity
        )
        return jsonify({"message": "Pet fetch job created", "jobId": job_id})
    except Exception as e:
        logger.exception(f"Failed to create pet fetch job: {e}")
        return jsonify({"error": "Failed to create pet fetch job"}), 500

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["PUT"])
@validate_request(dict)  # generic dict for update payload
async def update_pet(data: dict, pet_id: str):
    try:
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid update data"}), 400
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["DELETE"])
async def delete_pet(pet_id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet deleted successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete pet"}), 500

@app.route("/pets/funfact", methods=["POST"])
@validate_request(FunFactRequest)
async def get_fun_fact(data: FunFactRequest):
    import random
    fun_fact = random.choice(fun_facts_cache)
    return jsonify({"funFact": fun_fact})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)