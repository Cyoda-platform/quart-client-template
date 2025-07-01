from dataclasses import dataclass
from typing import Optional, List

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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
        except Exception:
            logger.exception("Failed to fetch pets from Petstore API")
            return []

# Workflow function for 'pet' entity
async def process_pet(entity: dict) -> dict:
    if "tags" not in entity or not isinstance(entity["tags"], list):
        entity["tags"] = []
    else:
        entity["tags"] = [str(t) for t in entity["tags"] if isinstance(t, (str, int, float)) and str(t).strip()]

    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()

    entity["updatedAt"] = datetime.utcnow().isoformat()

    # Placeholder for adding supplementary entities of different model if needed
    # for tag_name in entity["tags"]:
    #     try:
    #         await entity_service.add_item(
    #             token=cyoda_auth_service,
    #             entity_model="tag",
    #             entity_version=ENTITY_VERSION,
    #             entity={"name": tag_name},
    #             workflow=None
    #         )
    #     except Exception:
    #         logger.exception(f"Failed to add tag entity for tag {tag_name}")

    return entity

# Workflow function for 'fetch_pets_job' entity to start asynchronous fetch and add pets
async def process_fetch_pets_job_entity(entity: dict) -> dict:
    status = None
    category = None
    if isinstance(entity.get("filter"), dict):
        status = entity["filter"].get("status")
        category = entity["filter"].get("category")

    async def fetch_and_add():
        pets = await fetch_pets_from_petstore(status, category)
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
            except Exception:
                logger.exception("Failed to add pet in fetch job workflow")

    asyncio.create_task(fetch_and_add())

    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    entity["updatedAt"] = datetime.utcnow().isoformat()

    return entity

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

@routes_bp.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    job_entity = {
        "filter": {
            "status": data.filter.status,
            "category": data.filter.category,
        }
    }
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="fetch_pets_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity
        )
        return jsonify({"message": "Data fetch initiated", "job_id": str(job_id)})
    except Exception:
        logger.exception("Failed to create fetch pets job entity")
        return jsonify({"message": "Failed to initiate data fetch"}), 500

@routes_bp.route("/pets", methods=["GET"])
async def list_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception:
        logger.exception("Failed to list pets")
        return jsonify({"message": "Failed to list pets"}), 500

@routes_bp.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)
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
    except Exception:
        logger.exception("Failed to add pet")
        return jsonify({"message": "Failed to add pet"}), 500

@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
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
    except Exception:
        logger.exception(f"Failed to get pet {pet_id}")
        return jsonify({"message": "Failed to get pet"}), 500

@routes_bp.route("/pets/update/<string:pet_id>", methods=["POST"])
@validate_request(UpdatePetRequest)
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

        if data.name is not None:
            pet["name"] = data.name
        if data.category is not None:
            pet["category"] = data.category
        if data.status is not None:
            pet["status"] = data.status
        if data.tags is not None:
            pet["tags"] = data.tags

        pet = await process_pet(pet)

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
    except Exception:
        logger.exception(f"Failed to update pet {pet_id}")
        return jsonify({"message": "Failed to update pet"}), 500