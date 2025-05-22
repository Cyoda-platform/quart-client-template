from datetime import datetime
import logging
from dataclasses import dataclass
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

# Data classes for request validation
@dataclass
class FetchPetsRequest:
    status: str
    type: Optional[str] = None

@dataclass
class FilterPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None

@dataclass
class AdoptPetRequest:
    pet_id: str  # changed to string id
    adopter_name: str
    adopter_contact: str

def map_petstore_pet(pet: Dict) -> Dict:
    import random
    return {
        "id": str(pet.get("id")),  # changed id to string
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", "unknown") if pet.get("category") else "unknown",
        "status": pet.get("status", "available"),
        "age": random.randint(1, 10),  # TODO: Replace with real age if available
    }

# Workflow function applied to pet entity before persistence on fetch/add
async def process_pet(entity: Dict) -> None:
    # Normalize status and add last processed timestamp
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    entity["last_processed_at"] = datetime.utcnow().isoformat() + "Z"

# Workflow function applied to pet entity before persistence on adoption update
async def process_pet_adoption(entity: Dict) -> None:
    entity["status"] = "adopted"
    entity["adopted_at"] = datetime.utcnow().isoformat() + "Z"

pets_cache_ids: List[str] = []
filtered_cache_ids: List[str] = []

@routes_bp.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    status = data.status
    pet_type = data.type
    if status not in {"available", "pending", "sold"}:
        return jsonify({"error": "Invalid or missing status"}), 400
    params = {"status": status}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://petstore.swagger.io/v2/pet/findByStatus", params=params)
            response.raise_for_status()
            pets_data = response.json()
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch data from external Petstore API"}), 502
    if pet_type:
        pets_data = [p for p in pets_data if (p.get("category", {}).get("name") or "").lower() == pet_type.lower()]
    mapped_pets = [map_petstore_pet(p) for p in pets_data]

    global pets_cache_ids, filtered_cache_ids
    pets_cache_ids = []
    filtered_cache_ids = []

    for pet in mapped_pets:
        try:
            pet_copy = pet.copy()
            pet_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_copy
            )
            pets_cache_ids.append(str(pet_id))
        except Exception as e:
            logger.exception(e)

    filtered_cache_ids = pets_cache_ids.copy()

    return jsonify({"message": "Pets data fetched and stored", "count": len(mapped_pets)})

@routes_bp.route("/pets/filter", methods=["POST"])
@validate_request(FilterPetsRequest)
async def filter_pets(data: FilterPetsRequest):
    pet_type = data.type
    status = data.status
    min_age = data.min_age
    max_age = data.max_age

    try:
        all_pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets from entity service"}), 502

    def pet_matches(pet: Dict) -> bool:
        if pet_type and pet.get("type", "").lower() != pet_type.lower():
            return False
        if status and pet.get("status", "").lower() != status.lower():
            return False
        if min_age is not None and pet.get("age", 0) < min_age:
            return False
        if max_age is not None and pet.get("age", 0) > max_age:
            return False
        return True

    filtered = [p for p in all_pets if pet_matches(p)]

    global filtered_cache_ids
    filtered_cache_ids = [str(p.get("id")) for p in filtered]

    return jsonify({"pets": filtered})

@routes_bp.route("/pets", methods=["GET"])
async def get_pets():
    global filtered_cache_ids
    pets = []
    for pet_id in filtered_cache_ids:
        try:
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
            )
            if pet:
                pets.append(pet)
        except Exception as e:
            logger.exception(e)
    return jsonify({"pets": pets})

@routes_bp.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)
async def adopt_pet(data: AdoptPetRequest):
    pet_id = str(data.pet_id)
    adopter_name = data.adopter_name
    adopter_contact = data.adopter_contact

    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 502

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    # Add adopter info to entity before update
    pet["adopter_name"] = adopter_name
    pet["adopter_contact"] = adopter_contact

    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update pet adoption status"}), 502

    logger.info(f"Adoption processed for pet_id={pet_id} by {adopter_name}")
    return jsonify({"message": "Adoption processed", "pet_id": pet_id, "status": "adopted"})