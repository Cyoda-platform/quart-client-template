import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

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
    petId: int
    adopterName: str
    contact: str

@dataclass
class PetFunFacts:
    type: Optional[str] = None

# Local in-memory cache for pet details and adoption status
pet_cache: Dict[int, Dict[str, Any]] = {}
adoption_status: Dict[int, bool] = {}

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
        pet_cache[pet["id"]] = pet

    return filtered

async def check_pet_availability(pet_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pet {pet_id}: {e}")
            return False
    return pet.get("status") == "available"

async def process_adoption(pet_id: int, adopter_name: str, contact: str) -> Dict[str, Any]:
    available = await check_pet_availability(pet_id)
    if not available:
        return {"success": False, "message": f"Pet id {pet_id} is not available for adoption."}
    adoption_status[pet_id] = True
    pet = pet_cache.get(pet_id)
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
    result = await process_adoption(data.petId, data.adopterName, data.contact)
    return jsonify(result)

@app.route('/pets/fun-facts', methods=['POST'])
@validate_request(PetFunFacts)  # Workaround: validation decorators placement issue in quart-schema for POST
async def pets_fun_facts(data: PetFunFacts):
    fact = await get_fun_pet_fact(data.type)
    return jsonify({"fact": fact})

@app.route('/pets/<int:pet_id>', methods=['GET'])
async def pets_get(pet_id: int):
    pet = pet_cache.get(pet_id)
    if not pet:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                resp.raise_for_status()
                pet = resp.json()
                pet_cache[pet_id] = pet
            except Exception as e:
                logger.exception(f"Failed to fetch pet {pet_id}: {e}")
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