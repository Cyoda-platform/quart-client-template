import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
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
class AgeRange:
    min: int
    max: int

@dataclass
class SearchPets:
    type: Optional[str]
    status: Optional[str]
    ageRange: Optional[AgeRange]

@dataclass
class PetDetailsRequest:
    petId: str

@dataclass
class AddPetRequest:
    name: str
    type: Optional[str]
    status: Optional[str]
    description: Optional[str]

class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._data[key] = value

cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def process_pet(entity: Dict[str, Any]) -> None:
    # Default status
    if not entity.get('status'):
        entity['status'] = 'available'

    pet_type = entity.get('type')
    if pet_type:
        pet_type = pet_type.lower()
        entity['type'] = pet_type
    else:
        pet_type = None

    fun_facts = {
        "dog": "Dogs have about 1,700 taste buds!",
        "cat": "Cats have whiskers that help them sense their surroundings.",
        "bird": "Some birds can mimic human speech."
    }
    toys = {
        "dog": ["ball", "frisbee"],
        "cat": ["feather wand", "laser pointer"],
        "bird": ["mirror", "bell"]
    }

    entity['funFact'] = fun_facts.get(pet_type, "Pets bring joy to our lives!")
    entity['recommendedToys'] = toys.get(pet_type, ["toy"])
    logger.info(f"Workflow processed pet entity: {entity}")

async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> list:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": filters.get("status", "available")}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Error fetching pets from Petstore: {e}")
        return []

    def matches_filters(pet: dict) -> bool:
        if filters.get("type"):
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type != filters["type"].lower():
                return False
        # AgeRange not applied due to API limitation
        return True

    return [pet for pet in pets if matches_filters(pet)]

async def fetch_pet_details_from_petstore(pet_id: int) -> Optional[Dict[str, Any]]:
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            pet = resp.json()
            if "code" in pet and pet["code"] != 200:
                return None
            return pet
    except Exception as e:
        logger.exception(f"Error fetching pet details from Petstore: {e}")
        return None

def enrich_pet_details(pet: Dict[str, Any]) -> Dict[str, Any]:
    pet_type = pet.get("category", {}).get("name", "").lower() if "category" in pet else pet.get("type", "")
    pet_type = pet_type.lower() if pet_type else None
    fun_facts = {
        "dog": "Dogs have about 1,700 taste buds!",
        "cat": "Cats have whiskers that help them sense their surroundings.",
        "bird": "Some birds can mimic human speech."
    }
    toys = {
        "dog": ["ball", "frisbee"],
        "cat": ["feather wand", "laser pointer"],
        "bird": ["mirror", "bell"]
    }
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet_type,
        "age": None,
        "status": pet.get("status"),
        "description": pet.get("description"),
        "funFact": fun_facts.get(pet_type, "Pets bring joy to our lives!"),
        "recommendedToys": toys.get(pet_type, ["toy"])
    }

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPets)
async def pets_search(data: SearchPets):
    filters = {
        "type": data.type,
        "status": data.status or "available",
        "ageRange": {"min": data.ageRange.min, "max": data.ageRange.max} if data.ageRange else None
    }
    logger.info(f"Received /pets/search with filters: {filters}")

    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": []
        }
    }
    if filters["status"]:
        condition["cyoda"]["conditions"].append({
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": filters["status"],
            "type": "simple"
        })
    if filters["type"]:
        condition["cyoda"]["conditions"].append({
            "jsonPath": "$.type",
            "operatorType": "EQUALS",
            "value": filters["type"],
            "type": "simple"
        })

    try:
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(e)
        pets = []

    def simplify_pet(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("type"),
            "age": None,
            "status": pet.get("status"),
            "description": pet.get("description")
        }
    simplified_pets = [simplify_pet(p) for p in pets]

    await cache.set("last_search_results", simplified_pets)
    return jsonify({"pets": simplified_pets})

@app.route("/pets", methods=["GET"])
async def pets_get_last_search():
    pets = await cache.get("last_search_results")
    return jsonify({"pets": pets or []})

@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_id = str(data.petId)
    logger.info(f"Received /pets/details for petId: {pet_id}")

    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        pet = None

    if pet is None:
        pet_external = await fetch_pet_details_from_petstore(int(pet_id))
        if pet_external is None:
            return jsonify({"error": "Pet not found"}), 404
        pet = enrich_pet_details(pet_external)
    else:
        pet = enrich_pet_details(pet)

    await cache.set(f"pet_details_{pet_id}", pet)
    return jsonify(pet)

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pets_get_details(pet_id: str):
    pet = await cache.get(f"pet_details_{pet_id}")
    if pet is None:
        return jsonify({"error": "Pet details not cached. Please POST /pets/details first."}), 404
    return jsonify(pet)

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)
async def add_pet(data: AddPetRequest):
    pet_data = {
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "description": data.description
    }
    logger.info(f"Adding new pet with data: {pet_data}")

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_data
        )
    except Exception as e:
        logger.exception(f"Error adding pet: {e}")
        return jsonify({"error": "Failed to add pet"}), 500

    return jsonify({"id": entity_id})

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)