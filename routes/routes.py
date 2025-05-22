from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_querystring

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
    status: Optional[str] = None
    type: Optional[str] = None

@dataclass
class PetsFetchRequest:
    filter: PetFetchFilter
    enhance: Optional[bool] = False

@dataclass
class PetsGetQuery:
    job_id: str

@dataclass
class PetsFilterFilter:
    type: Optional[str] = None
    status: Optional[str] = None
    personality: Optional[str] = None

@dataclass
class PetsFilterRequest:
    job_id: str
    filter: PetsFilterFilter

@dataclass
class PetAddRequest:
    pet: Dict[str, Any]

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def process_petstore_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Processing petstore_pet entity workflow")
    entity.setdefault("processed_at", datetime.utcnow().isoformat())
    if "personality" not in entity:
        entity["personality"] = "adorable and unique"
    return entity

async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str]) -> List[Dict[str, Any]]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from petstore: {e}")
            return []
    if pet_type:
        pet_type_lower = pet_type.lower()
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type_lower]
    return pets

def add_personality_traits(pets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    personality_map = {
        "cat": [
            "playful and curious",
            "lazy and cuddly",
            "mischievous and clever",
            "independent and mysterious",
        ],
        "dog": [
            "friendly and loyal",
            "energetic and goofy",
            "calm and protective",
            "eager and attentive",
        ],
    }
    import random
    enhanced = []
    for pet in pets:
        pet_copy = pet.copy()
        pet_type = pet_copy.get("category", {}).get("name", "").lower()
        pet_copy["personality"] = random.choice(personality_map.get(pet_type, ["adorable and unique"]))
        enhanced.append(pet_copy)
    return enhanced

async def process_pet_fetch_job(entity: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Started processing pet_fetch_job id={entity.get('id', '(no id)')}")
    try:
        filt = entity.get("filter", {})
        status = filt.get("status")
        pet_type = filt.get("type")
        pets = await fetch_pets_from_petstore(status, pet_type)
        logger.info(f"Fetched {len(pets)} pets for pet_fetch_job")
        if entity.get("enhance", False):
            pets = add_personality_traits(pets)
            logger.info("Enhanced pets with personality traits")
        entity["pets"] = pets
        entity["status"] = "done"
        entity["finished_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Error in pet_fetch_job workflow")
        entity["status"] = "error"
        entity["error_message"] = str(e)
        entity["pets"] = []
    return entity

@routes_bp.route("/pets/fetch", methods=["POST"])
@validate_request(PetsFetchRequest)
async def pets_fetch(data: PetsFetchRequest):
    entity_data = {
        "filter": asdict(data.filter),
        "enhance": data.enhance or False,
        "status": "processing",
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        return jsonify({"job_id": entity_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(f"Failed to create pet_fetch_job entity: {e}")
        return jsonify({"error": "Failed to start pet fetch job"}), 500

@routes_bp.route("/pets", methods=["GET"])
@validate_querystring(PetsGetQuery)
async def pets_get():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400
    try:
        job_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_job",
            entity_version=ENTITY_VERSION,
            entity_id=job_id
        )
        if not job_entity:
            return jsonify({"error": f"job_id {job_id} not found"}), 404
        status = job_entity.get("status", "unknown")
        pets = job_entity.get("pets", []) if status == "done" else []
        return jsonify({"status": status, "pets": pets})
    except Exception as e:
        logger.exception(f"Error fetching pet_fetch_job: {e}")
        return jsonify({"error": "Internal server error"}), 500

@routes_bp.route("/pets/filter", methods=["POST"])
@validate_request(PetsFilterRequest)
async def pets_filter(data: PetsFilterRequest):
    job_id = data.job_id
    f = data.filter
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400
    try:
        job_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_job",
            entity_version=ENTITY_VERSION,
            entity_id=job_id
        )
        if not job_entity:
            return jsonify({"error": f"job_id {job_id} not found"}), 404
        if job_entity.get("status") != "done":
            return jsonify({"error": "pets data not ready"}), 400
        pets = job_entity.get("pets", [])
        def match(p: Dict[str, Any]) -> bool:
            if f.type and p.get("category", {}).get("name", "").lower() != f.type.lower():
                return False
            if f.status and p.get("status", "").lower() != f.status.lower():
                return False
            if f.personality and f.personality.lower() not in p.get("personality", "").lower():
                return False
            return True
        filtered = [p for p in pets if match(p)]
        return jsonify({"pets": filtered})
    except Exception as e:
        logger.exception(f"Error filtering pets for job_id {job_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@routes_bp.route("/pets/add", methods=["POST"])
@validate_request(PetAddRequest)
async def pets_add(data: PetAddRequest):
    pet_entity = data.pet
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="petstore_pet",
            entity_version=ENTITY_VERSION,
            entity=pet_entity
        )
        return jsonify({"entity_id": entity_id}), 201
    except Exception as e:
        logger.exception(f"Error adding petstore_pet entity: {e}")
        return jsonify({"error": "Failed to add pet entity"}), 500