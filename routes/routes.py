from datetime import datetime, timezone
import logging
from quart import Blueprint, request, abort, jsonify
from quart_schema import validate, validate_request

from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# PETSTORE_BASE_URL and Cache class moved as is from original for context
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

import asyncio
from typing import Dict, List, Optional
import httpx
from dataclasses import dataclass

class Cache:
    def __init__(self):
        self.adopted_pets: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()

cache = Cache()

@dataclass
class SearchPets:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class AdoptPet:
    petid: str

@dataclass
class FunFactsRequest:
    type: Optional[str] = None
    name: Optional[str] = None

async def fetch_pets_from_petstore(type_: Optional[str] = None, status: Optional[str] = None, name: Optional[str] = None) -> List[Dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        if status:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
            except Exception as e:
                logger.exception(f"Error fetching pets by status from Petstore: {e}")
                pets = []
        else:
            pets = []
            for s in ["available", "pending", "sold"]:
                try:
                    r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": s})
                    r.raise_for_status()
                    pets.extend(r.json())
                except Exception as e:
                    logger.exception(f"Error fetching pets by status '{s}' from Petstore: {e}")

        def matches_criteria(pet):
            if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
                return False
            if name and name.lower() not in pet.get("name", "").lower():
                return False
            return True

        filtered = [pet for pet in pets if matches_criteria(pet)]
        return filtered

def generate_fun_description(pet: Dict) -> str:
    jokes = {
        "cat": "Did you know cats can make over 100 vocal sounds? Purrhaps it99s true!",
        "dog": "Dogs99 noses are wet to help absorb scent chemicals. Sniff-tastic!",
        "bird": "Birds are the only animals with feathers, they really know how to dress up!",
    }
    pet_type = pet.get("category", {}).get("name", "").lower()
    name = pet.get("name", "Your new friend")
    return jokes.get(pet_type, f"{name} is as awesome as any pet you can imagine!")

@routes_bp.route("/pets/search", methods=["POST"])
@validate_request(SearchPets)
async def pets_search(data: SearchPets):
    pets_raw = await fetch_pets_from_petstore(data.type, data.status, data.name)
    pets = []
    for p in pets_raw:
        pets.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "description": generate_fun_description(p),
                "imageUrl": p.get("photoUrls")[0] if p.get("photoUrls") else None,
            }
        )
    return jsonify({"pets": pets})

@routes_bp.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPet)
async def pets_adopt(data: AdoptPet):
    adoption_entity_data = {
        "id": str(data.petid),
    }

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_adoption",
            entity_version=entity_service.ENTITY_VERSION if hasattr(entity_service, 'ENTITY_VERSION') else None,
            entity=adoption_entity_data
        )
    except Exception as e:
        logger.exception(f"Adoption failed: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({"success": True, "message": f"Pet adopted successfully!", "entityId": entity_id})

@routes_bp.route("/pets/adopted", methods=["GET"])
async def pets_adopted():
    async with cache.lock:
        adopted_list = list(cache.adopted_pets.values())
    return jsonify({"adoptedPets": adopted_list})

@routes_bp.route("/pets/fun-facts", methods=["POST"])
@validate_request(FunFactsRequest)
async def pets_fun_facts(data: FunFactsRequest):
    type_ = data.type.lower() if data.type else None
    name = data.name

    facts = {
        "cat": "Cats sleep for 70% of their lives. Talk about a catnap!",
        "dog": "Dogs99 sense of smell is at least 40x better than humans99!",
        "bird": "Some birds can mimic human speech amazingly well.",
    }

    if type_ in facts:
        fact = facts[type_]
    elif name:
        fact = f"{name} is truly one of a kind and full of surprises!"
    else:
        fact = "Pets make life pawsome! "

    return jsonify({"fact": fact})