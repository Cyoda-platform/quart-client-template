from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

# POST /pets - handle add or update pet
@routes_bp.route("/pets", methods=["POST"])
@validate_request(PetAction)
async def pets_post(data: PetAction):
    pet_entity = data.pet or {}
    pet_entity["action"] = data.action

    # Since we want to persist pet entity with workflow, just add or update
    if data.action == "add":
        try:
            id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_entity
            )
            return jsonify({"id": id}), 201
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to add pet"}), 500

    elif data.action == "update":
        pet_id = pet_entity.get("id")
        if not pet_id:
            return jsonify({"error": "Pet id required for update"}), 400
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_entity,
                technical_id=pet_id,
                meta={}
            )
            updated_pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
            )
            return jsonify(updated_pet)
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to update pet"}), 500

    else:
        return jsonify({"error": "Unsupported action"}), 400

# GET /pets/<pet_id> - fetch pet, no persistence, no workflow
@routes_bp.route("/pets/<pet_id>", methods=["GET"])
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

# POST /pets/search - search pets from petstore (no persistence, no workflow)
@routes_bp.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def search_pets(data: PetSearch):
    pets = await search_pets_from_petstore(data.category, data.status, data.tags)
    return jsonify({"pets": pets})

# GET /pets/random-fact - fetch random fact (no persistence, no workflow)
@routes_bp.route("/pets/random-fact", methods=["GET"])
async def random_fact():
    fact = await get_random_pet_fact()
    return jsonify({"fact": fact})