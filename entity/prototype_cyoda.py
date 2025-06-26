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

entity_jobs: dict = {}
PET_ENTITY_NAME = "pet"

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

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

async def process_fetch_pets_job(job_id: str, type_: Optional[str], status: Optional[str]):
    try:
        pets = await fetch_pets_from_petstore(type_, status)
        # Add each pet to entity_service asynchronously, but do not wait for all
        for pet in pets:
            # Ensure id is not included in data sent to add_item, as id is assigned by entity_service
            pet_data = pet.copy()
            pet_data.pop("id", None)
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=pet_data
            )
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["count"] = len(pets)
        logger.info(f"Fetched and stored {len(pets)} pets for job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    type_ = data.type
    status = data.status
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_fetch_pets_job(job_id, type_, status))
    return jsonify({"message": "Pets fetch started", "jobId": job_id}), 202

@validate_querystring(GetPetsQuery)
@app.route("/pets", methods=["GET"])
async def pets_list():
    args = request.args
    type_filter = args.get("type")
    status_filter = args.get("status")

    # Build condition dict for filtering if provided
    condition = None
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
    if conditions_list:
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": conditions_list
            }
        }

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
    pet = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model=PET_ENTITY_NAME,
        entity_version=ENTITY_VERSION,
        technical_id=pet_id
    )
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
    # TODO: implement category-based fact selection if needed
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})

FUN_PET_FACTS = [
    "Cats sleep for 70% of their lives!",
    "Dogs have three eyelids.",
    "Rabbits can't vomit.",
    "Goldfish can see both infrared and ultraviolet light.",
    "Parrots will selflessly help each other out.",
]

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)