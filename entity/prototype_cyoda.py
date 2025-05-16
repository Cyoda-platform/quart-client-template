import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class PetAdopt:
    pet_id: str  # changed to string per instructions
    adopter_name: str
    contact: str

@dataclass
class PetFunFacts:
    type: Optional[str] = None

# Local in-memory cache for adoption status only
adoption_status: Dict[str, bool] = {}

PETSTORE_API_BASE = 'https://petstore.swagger.io/v2'

async def fetch_pets_from_petstore(search_criteria: Dict[str, Any]) -> list:
    async with httpx.AsyncClient() as client:
        status = search_criteria.get("status", "available")
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets: {e}")
            return []

    pet_type = search_criteria.get("type")
    name_filter = (search_criteria.get("name") or "").lower()

    filtered = []
    for pet in pets:
        category = pet.get("category", {})
        category_name = (category.get("name") or "").lower()
        if pet_type and pet_type.lower() != category_name:
            continue
        pet_name = (pet.get("name") or "").lower()
        if name_filter and name_filter not in pet_name:
            continue
        filtered.append(pet)

    return filtered

async def check_pet_availability(pet_id: str) -> bool:
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(f"Failed to fetch pet {pet_id}: {e}")
        return False
    return pet.get("status") == "available" if pet else False

async def process_adoption(pet_id: str, adopter_name: str, contact: str) -> Dict[str, Any]:
    available = await check_pet_availability(pet_id)
    if not available:
        return {"success": False, "message": f"Pet id {pet_id} is not available for adoption."}
    adoption_status[pet_id] = True
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception:
        pet = None
    pet_name = pet.get("name") if pet else f"#{pet_id}"
    return {"success": True, "message": f"Pet {pet_name} adopted successfully!"}

async def get_fun_pet_fact(pet_type: Optional[str] = None) -> str:
    facts = {
        "cat": ["Cats sleep for 70% of their lives.", "A group of cats is called a clowder."],
        "dog": ["Dogs can learn more than 1000 words!", "Dogs have three eyelids."],
        "default": ["Pets bring joy to our lives!", "Animals have a sense of time and can miss you."]
    }
    selected = facts.get((pet_type or "").lower(), facts["default"])
    import random
    return random.choice(selected)

@app.route('/pets/search', methods=['POST'])
@validate_request(PetSearch)  # Workaround: validation decorators placement issue in quart-schema for POST
async def pets_search(data: PetSearch):
    pets = await fetch_pets_from_petstore(data.__dict__)
    results = []
    for pet in pets:
        results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
            "description": pet.get("description") or ""
        })
    return jsonify({"results": results})

@app.route('/pets/adopt', methods=['POST'])
@validate_request(PetAdopt)  # Workaround: validation decorators placement issue in quart-schema for POST
async def pets_adopt(data: PetAdopt):
    result = await process_adoption(data.pet_id, data.adopter_name, data.contact)
    return jsonify(result)

@app.route('/pets/fun-facts', methods=['POST'])
@validate_request(PetFunFacts)  # Workaround: validation decorators placement issue in quart-schema for POST
async def pets_fun_facts(data: PetFunFacts):
    fact = await get_fun_pet_fact(data.type)
    return jsonify({"fact": fact})

@app.route('/pets/<string:pet_id>', methods=['GET'])  # pet_id is string now
async def pets_get(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(f"Failed to fetch pet {pet_id}: {e}")
        return jsonify({"message": "Pet not found"}), 404
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify({
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "description": pet.get("description") or ""
    })

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)