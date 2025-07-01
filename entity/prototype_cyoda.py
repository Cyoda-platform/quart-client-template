from dataclasses import dataclass
from typing import Optional, List

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

entity_jobs = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(filter_status, filter_category):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": filter_status or "available"}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if filter_category:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == filter_category.lower()]
            return pets
        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            return []

async def process_fetch_pets_job(job_id, status, category):
    try:
        pets = await fetch_pets_from_petstore(status, category)
        # Clear all existing pets in entity_service - no direct function, so clear local cache only
        # Instead, we skip clearing local cache, as all pets are stored in entity_service
        # Add pets to entity_service
        # We don't have batch add, so add one by one
        # There is no delete all, so we just add new pets

        # No local cache now, just add pets to entity_service
        # We can add pets asynchronously
        for pet in pets:
            try:
                pet_data = {
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "tags": [t.get("name") for t in pet.get("tags", []) if t.get("name")]
                }
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data
                )
            except Exception as e:
                logger.exception(f"Failed to add pet from fetch job: {pet}")
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        # Count pets in entity_service: no direct count, so skip pets_count or just set None
        entity_jobs[job_id]["pets_count"] = None
        logger.info(f"Fetch pets job {job_id} completed.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Fetch pets job {job_id} failed.")

@dataclass
class Filter:
    status: str
    category: Optional[str] = None

@dataclass
class FetchPetsRequest:
    filter: Filter

@dataclass
class AddPetRequest:
    name: str
    category: str
    status: str
    tags: List[str]

@dataclass
class UpdatePetRequest:
    name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # Workaround: validate_request after route due to quart-schema defect
async def pets_fetch(data: FetchPetsRequest):
    status = data.filter.status
    category = data.filter.category
    job_id = f"fetch_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_fetch_pets_job(job_id, status, category))
    return jsonify({"message": "Data fetch initiated", "job_id": job_id})

@app.route("/pets", methods=["GET"])
async def list_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception("Failed to list pets")
        return jsonify({"message": "Failed to list pets"}), 500

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)  # Workaround: validate_request after route due to quart-schema defect
async def add_pet(data: AddPetRequest):
    pet_data = {
        "name": data.name,
        "category": data.category,
        "status": data.status,
        "tags": data.tags,
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_data
        )
        logger.info(f"Added pet {pet_id}")
        return jsonify({"message": "Pet added successfully", "pet_id": str(pet_id)})
    except Exception as e:
        logger.exception("Failed to add pet")
        return jsonify({"message": "Failed to add pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"message": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(f"Failed to get pet {pet_id}")
        return jsonify({"message": "Failed to get pet"}), 500

@app.route("/pets/update/<string:pet_id>", methods=["POST"])
@validate_request(UpdatePetRequest)  # Workaround: validate_request after route due to quart-schema defect
async def update_pet(data: UpdatePetRequest, pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"message": "Pet not found"}), 404

        # Update pet dict with new data if present
        if data.name is not None:
            pet["name"] = data.name
        if data.category is not None:
            pet["category"] = data.category
        if data.status is not None:
            pet["status"] = data.status
        if data.tags is not None:
            pet["tags"] = data.tags

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )
        logger.info(f"Updated pet {pet_id}")
        return jsonify({"message": "Pet updated successfully"})
    except Exception as e:
        logger.exception(f"Failed to update pet {pet_id}")
        return jsonify({"message": "Failed to update pet"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)