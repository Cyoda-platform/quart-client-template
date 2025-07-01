from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

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

# Workaround: due to quart-schema defect, place @validate_request after @app.route for POST endpoints

@dataclass
class SearchPets:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class AdoptPet:
    petid: str  # changed to string, lowercase id field

@dataclass
class FunFactsRequest:
    type: Optional[str] = None
    name: Optional[str] = None

# In-memory cache for adopted pets to simulate persistence where entity_service is not used
class Cache:
    def __init__(self):
        self.adopted_pets: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()

cache = Cache()

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(
    type_: Optional[str] = None, status: Optional[str] = None, name: Optional[str] = None
) -> List[Dict]:
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
        "cat": "Did you know cats can make over 100 vocal sounds? Purrhaps it’s true!",
        "dog": "Dogs’ noses are wet to help absorb scent chemicals. Sniff-tastic!",
        "bird": "Birds are the only animals with feathers, they really know how to dress up!",
    }
    pet_type = pet.get("category", {}).get("name", "").lower()
    name = pet.get("name", "Your new friend")
    return jokes.get(pet_type, f"{name} is as awesome as any pet you can imagine!")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPets)
async def pets_search(data: SearchPets):
    type_ = data.type
    status = data.status
    name = data.name

    pets_raw = await fetch_pets_from_petstore(type_, status, name)
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

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPet)
async def pets_adopt(data: AdoptPet):
    pet_id = str(data.petid)  # ensure string id

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return jsonify({"success": False, "message": "Pet not found"}), 404
            logger.exception(e)
            return jsonify({"success": False, "message": "Error fetching pet info"}), 500
        except Exception as e:
            logger.exception(e)
            return jsonify({"success": False, "message": "Error fetching pet info"}), 500

    if pet.get("status") != "available":
        return jsonify({"success": False, "message": "Pet is not available for adoption"}), 400

    async with cache.lock:
        if pet_id in cache.adopted_pets:
            return jsonify({"success": False, "message": "Pet already adopted"}), 400
        cache.adopted_pets[pet_id] = {
            "id": pet_id,
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "adoptionDate": datetime.utcnow().isoformat() + "Z",
            "message": f"Congratulations on adopting {pet.get('name')}! 🎉🐾",
        }
    return jsonify({"success": True, "message": f"Pet {pet.get('name')} adopted successfully!"})

@app.route("/pets/adopted", methods=["GET"])
async def pets_adopted():
    async with cache.lock:
        adopted_list = list(cache.adopted_pets.values())
    return jsonify({"adoptedPets": adopted_list})

@app.route("/pets/fun-facts", methods=["POST"])
@validate_request(FunFactsRequest)
async def pets_fun_facts(data: FunFactsRequest):
    type_ = data.type.lower() if data.type else None
    name = data.name

    facts = {
        "cat": "Cats sleep for 70% of their lives. Talk about a catnap!",
        "dog": "Dogs’ sense of smell is at least 40x better than humans’!",
        "bird": "Some birds can mimic human speech amazingly well.",
    }

    if type_ in facts:
        fact = facts[type_]
    elif name:
        fact = f"{name} is truly one of a kind and full of surprises!"
    else:
        fact = "Pets make life pawsome! 🐾😺🐶"

    return jsonify({"fact": fact})