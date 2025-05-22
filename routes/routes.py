from dataclasses import dataclass, asdict
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

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

@dataclass
class PetFetchFilter:
    type: str
    status: str

@dataclass
class PetFetchActions:
    markFavorite: Optional[List[str]] = None
    updateAdoptionStatus: Optional[Dict[str, str]] = None

@dataclass
class FetchRequest:
    filter: PetFetchFilter
    actions: PetFetchActions

@dataclass
class Adopter:
    name: str
    contact: str

@dataclass
class AdoptRequest:
    petId: str
    adopter: Adopter

favorites_cache: set = set()

PET_ENTITY_NAME = "pet"
ADOPTIONREQUEST_ENTITY_NAME = "adoptionrequest"

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[Dict]:
    valid_statuses = {"available", "pending", "sold"}
    statuses = [status] if status in valid_statuses else list(valid_statuses)
    pets = []
    async with httpx.AsyncClient() as client:
        for stat in statuses:
            try:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": stat})
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
            except Exception as e:
                logger.exception(f"Error fetching pets status={stat}: {e}")
    if pet_type and pet_type.lower() != "all":
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    normalized = []
    for pet in pets:
        normalized.append({
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "type": pet.get("category", {}).get("name", "other").lower(),
            "status": pet.get("status", "available"),
            "photoUrls": pet.get("photoUrls", []),
            "isFavorite": False,
        })
    return normalized

async def process_fetch_request(data: Dict) -> Dict:
    filter_ = data.get("filter", {})
    actions = data.get("actions", {})
    pet_type = filter_.get("type", "all")
    status = filter_.get("status", "all")

    pets = await fetch_pets_from_petstore(pet_type, status)

    for pet in pets:
        pet["isFavorite"] = pet["id"] in favorites_cache

    for pet_id in actions.get("markFavorite", []):
        favorites_cache.add(pet_id)

    for pid, new_status in (actions.get("updateAdoptionStatus") or {}).items():
        for pet in pets:
            if pet["id"] == pid:
                pet["status"] = new_status

    return {"pets": pets, "message": "Pets fetched and processed successfully."}

@routes_bp.route("/pets/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def pets_fetch(data: FetchRequest):
    try:
        result = await process_fetch_request(asdict(data))
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500

@routes_bp.route("/pets", methods=["GET"])
async def pets_get():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        for pet in pets:
            pet["isFavorite"] = pet["id"] in favorites_cache
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"pets": []})

@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"message": "Pet not found"}), 404
        pet["isFavorite"] = pet["id"] in favorites_cache
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500

@routes_bp.route("/pets", methods=["POST"])
@validate_request(dict)
async def create_pet(data):
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({"id": pet_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500

@routes_bp.route("/pets/<string:pet_id>", methods=["PUT"])
@validate_request(dict)
async def update_pet(pet_id: str, data):
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet updated successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500

@routes_bp.route("/pets/<string:pet_id>", methods=["DELETE"])
async def delete_pet(pet_id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet deleted successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500

@routes_bp.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)
async def pets_adopt(data: AdoptRequest):
    try:
        adoption_request_data = asdict(data)
        adoption_request_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ADOPTIONREQUEST_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=adoption_request_data
        )
        return jsonify({"success": True, "id": adoption_request_id, "message": "Adoption request received."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": str(e)}), 400