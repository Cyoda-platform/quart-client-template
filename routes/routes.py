import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class GetPetsQuery:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class FunFactRequest:
    category: Optional[str] = None

PET_ENTITY_NAME = "pet"
PET_FETCH_JOB_ENTITY_NAME = "pet_fetch_job"

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

FUN_PET_FACTS = [
    "Cats sleep for 70% of their lives!",
    "Dogs have three eyelids.",
    "Rabbits can't vomit.",
    "Goldfish can see both infrared and ultraviolet light.",
    "Parrots will selflessly help each other out.",
]

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> list:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            params = {}
            if status:
                params["status"] = status
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

async def process_pet(entity: dict) -> dict:
    entity["processedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Workflow process_pet: processing pet '{entity.get('name')}'")
    return entity

async def process_pet_fetch_job(entity: dict) -> dict:
    job_id = entity.get("id")
    type_ = entity.get("type")
    status_filter = entity.get("statusFilter")

    logger.info(f"Workflow process_pet_fetch_job: Starting fetch job {job_id} with type={type_} status={status_filter}")

    try:
        pets = await fetch_pets_from_petstore(type_, status_filter)
        logger.info(f"Fetched {len(pets)} pets from external API for job {job_id}")

        for pet in pets:
            pet_data = pet.copy()
            pet_data.pop("id", None)
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=pet_data
            )

        updated_entity = entity.copy()
        updated_entity["status"] = "completed"
        updated_entity["completedAt"] = datetime.utcnow().isoformat()
        updated_entity["count"] = len(pets)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_FETCH_JOB_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity=updated_entity
        )
        logger.info(f"Fetch job {job_id} completed successfully")
    except Exception as e:
        logger.exception(f"Fetch job {job_id} failed: {e}")
        updated_entity = entity.copy()
        updated_entity["status"] = "failed"
        updated_entity["error"] = str(e)
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=PET_FETCH_JOB_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity=updated_entity
            )
        except Exception as inner_e:
            logger.exception(f"Failed to update failed job status for job {job_id}: {inner_e}")
    return entity

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    job_entity = {
        "requestedAt": datetime.utcnow().isoformat(),
        "status": "processing",
        "type": data.type,
        "statusFilter": data.status
    }
    job_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=PET_FETCH_JOB_ENTITY_NAME,
        entity_version=ENTITY_VERSION,
        entity=job_entity
    )
    logger.info(f"Created pet fetch job entity with id {job_id}")
    return jsonify({"message": "Pets fetch started", "jobId": job_id}), 202

@validate_querystring(GetPetsQuery)
@app.route("/pets", methods=["GET"])
async def pets_list():
    args = request.args
    type_filter = args.get("type")
    status_filter = args.get("status")

    conditions_list = []
    if type_filter:
        conditions_list.append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": type_filter,
            "type": "simple"
        })
    if status_filter:
        conditions_list.append({
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": status_filter,
            "type": "simple"
        })
    condition = None
    if conditions_list:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": conditions_list
            }
        }

    try:
        if condition:
            pets = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            pets = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
            )
    except Exception as e:
        logger.exception(f"Failed to retrieve pets: {e}")
        return jsonify({"error": "Failed to retrieve pets"}), 500

    pets_simple = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name") if p.get("category") else None,
            "status": p.get("status"),
        }
        for p in pets
    ]
    return jsonify(pets_simple)

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pet_detail(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve pet {pet_id}: {e}")
        return jsonify({"error": "Failed to retrieve pet"}), 500

    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    pet_detail_response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag],
    }
    return jsonify(pet_detail_response)

@app.route("/fun/random-fact", methods=["POST"])
@validate_request(FunFactRequest)
async def fun_random_fact(data: FunFactRequest):
    import random
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
