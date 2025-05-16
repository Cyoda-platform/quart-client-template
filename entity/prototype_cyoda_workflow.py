import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)


@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None


@dataclass
class PetAdopt:
    pet_id: str
    adopter_name: str
    contact: str


@dataclass
class PetFunFacts:
    type: Optional[str] = None


@dataclass
class PetAdd:
    name: str
    category: Optional[Dict[str, Any]] = None
    status: Optional[str] = "available"
    photoUrls: Optional[list] = None
    description: Optional[str] = ""


# In-memory adoption status cache
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


async def get_fun_pet_fact(pet_type: Optional[str] = None) -> str:
    facts = {
        "cat": ["Cats sleep for 70% of their lives.", "A group of cats is called a clowder."],
        "dog": ["Dogs can learn more than 1000 words!", "Dogs have three eyelids."],
        "default": ["Pets bring joy to our lives!", "Animals have a sense of time and can miss you."]
    }
    selected = facts.get((pet_type or "").lower(), facts["default"])
    import random
    return random.choice(selected)


async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Set created_at timestamp if missing
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat() + "Z"

    # Default status to "available"
    if not entity.get("status"):
        entity["status"] = "available"

    # Enrich category metadata if category id present
    category = entity.get("category")
    if category and isinstance(category, dict):
        category_id = category.get("id")
        if category_id:
            try:
                category_entity = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="category",
                    entity_version=ENTITY_VERSION,
                    technical_id=category_id
                )
                if category_entity:
                    # Add supplementary entity with category metadata
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="category_metadata",
                        entity_version=ENTITY_VERSION,
                        entity={"category_id": category_id, "metadata": category_entity},
                    )
                    entity["category_metadata_loaded"] = True
            except Exception as ex:
                logger.warning(f"Failed to fetch or add category metadata for category_id={category_id}: {ex}")

    return entity


@app.route('/pets/search', methods=['POST'])
@validate_request(PetSearch)
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
@validate_request(PetAdopt)
async def pets_adopt(data: PetAdopt):
    available = await check_pet_availability(data.pet_id)
    if not available:
        return jsonify({"success": False, "message": f"Pet id {data.pet_id} is not available for adoption."})
    # Mark adoption in local cache
    adoption_status[data.pet_id] = True

    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=data.pet_id
        )
    except Exception:
        pet = None
    pet_name = pet.get("name") if pet else f"#{data.pet_id}"
    return jsonify({"success": True, "message": f"Pet {pet_name} adopted successfully!"})


@app.route('/pets/fun-facts', methods=['POST'])
@validate_request(PetFunFacts)
async def pets_fun_facts(data: PetFunFacts):
    fact = await get_fun_pet_fact(data.type)
    return jsonify({"fact": fact})


@app.route('/pets/<string:pet_id>', methods=['GET'])
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


@app.route('/pets/add', methods=['POST'])
@validate_request(PetAdd)
async def pets_add(data: PetAdd):
    entity_data = data.__dict__
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_pet
        )
    except Exception as e:
        logger.exception(f"Failed to add pet: {e}")
        return jsonify({"success": False, "message": "Failed to add pet"}), 500
    return jsonify({"success": True, "message": "Pet added successfully", "id": entity_id})


if __name__ == '__main__':
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)