from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
import uuid

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

entity_job: Dict[str, Dict[str, Any]] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
RANDOM_PET_FACTS_URL = "https://some-random-api.ml/facts/cat"

@dataclass
class PetAction:
    action: str
    pet: Optional[Dict[str, Any]]

@dataclass
class PetSearch:
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

async def fetch_pet_from_petstore(pet_id: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
            return pet
        except httpx.HTTPStatusError as e:
            logger.warning(f"Petstore API returned error for pet_id={pet_id}: {e}")
            return None
        except Exception as e:
            logger.exception(e)
            return None

async def search_pets_from_petstore(
    category: Optional[str], status: Optional[str], tags: Optional[List[str]]
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            params = {}
            if status:
                params["status"] = status
            else:
                params["status"] = "available,pending,sold"

            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()

            def matches(p):
                if category and (p.get("category", {}).get("name", "").lower() != category.lower()):
                    return False
                if tags:
                    pet_tags = [t["name"].lower() for t in p.get("tags", [])]
                    if not all(tag.lower() in pet_tags for tag in tags):
                        return False
                return True

            filtered = [p for p in pets if matches(p)]
            return filtered
        except Exception as e:
            logger.exception(e)
            return []

async def get_random_pet_fact() -> str:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(RANDOM_PET_FACTS_URL)
            r.raise_for_status()
            data = r.json()
            fact = data.get("fact")
            if not fact:
                fact = "Cats are mysterious and wonderful creatures!"
            return fact
        except Exception as e:
            logger.warning(f"Failed to fetch random pet fact: {e}")
            return "Cats are mysterious and wonderful creatures!"

async def process_entity(job_id: str, data: Dict[str, Any]):
    try:
        action = data.get("action")
        pet_data = data.get("pet", {})
        result_pet = None

        if action == "fetch":
            pet_id = str(pet_data.get("id", ""))
            if not pet_id:
                entity_job[job_id]["status"] = "error"
                return
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
            )
            if pet:
                result_pet = pet
            else:
                entity_job[job_id]["status"] = "not_found"
                return

        elif action == "add":
            pet_id = pet_data.get("id") or str(uuid.uuid4())
            pet_data["id"] = pet_id
            try:
                id = await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                )
                # just return id in response - here store pet_id as id for job result
                result_pet = {"id": id}
            except Exception as e:
                logger.exception(e)
                entity_job[job_id]["status"] = "error"
                return

        elif action == "update":
            pet_id = pet_data.get("id")
            if not pet_id:
                entity_job[job_id]["status"] = "error"
                return
            try:
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                    technical_id=pet_id,
                    meta={},
                )
                # get updated pet
                updated_pet = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    technical_id=pet_id,
                )
                if updated_pet:
                    result_pet = updated_pet
                else:
                    entity_job[job_id]["status"] = "not_found"
                    return
            except Exception as e:
                logger.exception(e)
                entity_job[job_id]["status"] = "error"
                return

        else:
            entity_job[job_id]["status"] = "error"
            return

        entity_job[job_id]["status"] = "done"
        entity_job[job_id]["result"] = result_pet

    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "error"

# POST /pets
@app.route("/pets", methods=["POST"])
@validate_request(PetAction)  # validation last for POST - workaround for quart_schema issue
async def pets_post(data: PetAction):
    job_id = str(uuid.uuid4())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# GET /pets/job-status/<job_id>
@app.route("/pets/job-status/<job_id>", methods=["GET"])
async def job_status(job_id):
    job = entity_job.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "done":
        return jsonify({"status": "done", "result": job.get("result")})
    else:
        return jsonify({"status": job["status"]})

# GET /pets/<pet_id>
@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

# POST /pets/search
@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)  # validation last for POST - workaround for quart_schema issue
async def search_pets(data: PetSearch):
    # Build condition for entity_service.get_items_by_condition
    # The condition format is not specified, so skip and fallback to petstore search as before
    pets = await search_pets_from_petstore(data.category, data.status, data.tags)
    return jsonify({"pets": pets})

# GET /pets/random-fact
@app.route("/pets/random-fact", methods=["GET"])
async def random_fact():
    fact = await get_random_pet_fact()
    return jsonify({"fact": fact})

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)