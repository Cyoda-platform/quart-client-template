from dataclasses import dataclass
import asyncio
import logging
from typing import Optional

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class AdoptPetRequest:
    petId: int

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"


async def process_pet_fetch_request(entity: dict):
    type_filter = entity.get("type")
    status_filter = entity.get("status") or "available"

    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status_filter}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore API: {e}")
            pets = []

    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]

    for pet in pets:
        try:
            pet_data = pet.copy()
            pet_data.pop("id", None)
            if not isinstance(pet_data, dict):
                continue
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data
            )
        except Exception as e:
            logger.exception(f"Failed to add pet to entity_service: {e}")

    entity['fetch_completed'] = True


async def process_pet(entity: dict):
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    if "category" in entity and isinstance(entity["category"], dict):
        if "name" in entity["category"] and isinstance(entity["category"]["name"], str):
            entity["category"]["name"] = entity["category"]["name"].lower()
    return entity


async def process_pet_adoption_request(entity: dict):
    pet_id = entity.get("pet_id")
    if not pet_id:
        entity["adoption_status"] = "failed"
        entity["error"] = "No pet_id provided"
        return entity

    get_url = f"{PETSTORE_BASE}/pet/{pet_id}"
    update_url = f"{PETSTORE_BASE}/pet"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(get_url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if not pet:
                entity["adoption_status"] = "failed"
                entity["error"] = "Pet not found"
                return entity

            pet["status"] = "adopted"
            resp_update = await client.put(update_url, json=pet, timeout=10)
            resp_update.raise_for_status()

            entity["adoption_status"] = "success"

        except Exception as e:
            logger.exception(f"Failed to adopt pet via external API: {e}")
            entity["adoption_status"] = "failed"
            entity["error"] = str(e)

    return entity


@routes_bp.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    fetch_request_entity = {
        "type": data.type,
        "status": data.status,
        "requested_at": str(asyncio.get_event_loop().time()),
        "fetch_completed": False,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=fetch_request_entity
        )
    except Exception as e:
        logger.exception(f"Failed to create pet_fetch_request entity: {e}")
        return jsonify({"error": "Failed to start pet fetch process"}), 500

    return jsonify({"message": "Pet fetch request accepted. Pets will be fetched and cached asynchronously."}), 202


@routes_bp.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)
async def adopt_pet(data: AdoptPetRequest):
    pet_id_str = str(data.petId)

    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id_str
        )
    except Exception as e:
        logger.exception(f"Error retrieving pet from entity_service: {e}")
        return jsonify({"error": "Internal server error."}), 500

    if not pet:
        return jsonify({"error": f"Pet with ID {pet_id_str} not found. Please fetch pets first."}), 404

    adoption_request_entity = {
        "pet_id": pet_id_str,
        "requested_at": str(asyncio.get_event_loop().time()),
        "adoption_status": "pending"
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_adoption_request",
            entity_version=ENTITY_VERSION,
            entity=adoption_request_entity
        )
    except Exception as e:
        logger.exception(f"Failed to create pet_adoption_request entity: {e}")
        return jsonify({"error": "Failed to start pet adoption process"}), 500

    return jsonify({"message": f"Adoption request for pet {pet_id_str} accepted."}), 202


@routes_bp.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(f"Failed to get pets from entity_service: {e}")
        return jsonify({"error": "Failed to retrieve pets."}), 500


@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": f"Pet with ID {pet_id} not found."}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(f"Failed to get pet from entity_service: {e}")
        return jsonify({"error": "Failed to retrieve pet."}), 500