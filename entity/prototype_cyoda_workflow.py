import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class QueryFilters:
    ageRange: Optional[List[int]]
    color: Optional[str]
    nameContains: Optional[str]

@dataclass
class PetsQuery:
    species: str
    status: str
    filters: QueryFilters

@dataclass
class UserInfo:
    name: str
    email: str

@dataclass
class AdoptionRequest:
    petId: str
    user: UserInfo

class InMemoryCache:
    def __init__(self):
        self._adoptions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def adopt_pet(self, pet_id: str, user_info: Dict[str, Any]) -> bool:
        async with self._lock:
            if pet_id in self._adoptions:
                return False
            self._adoptions[pet_id] = {
                "user": user_info,
                "adoptedAt": datetime.utcnow().isoformat()
            }
            return True

    async def is_adopted(self, pet_id: str) -> bool:
        async with self._lock:
            return pet_id in self._adoptions

cache = InMemoryCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

FUN_FACTS = [
    "Cats sleep for 70% of their lives",
    "Dogs have three eyelids",
    "Some birds can mimic human speech",
    "Cats have five toes on their front paws but only four on the back",
    "Dogs' sense of smell is about 40 times better than ours"
]

async def fetch_pets_from_petstore(status: str) -> List[Dict[str, Any]]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if not isinstance(pets, list):
                logger.warning("Unexpected pets response structure")
                return []
            return pets
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

def filter_pets(
    pets: List[Dict[str, Any]],
    species: str,
    age_range: Optional[List[int]],
    color: Optional[str],
    name_contains: Optional[str]
) -> List[Dict[str, Any]]:
    filtered = []
    for pet in pets:
        pet_species = pet.get("category", {}).get("name", "").lower()
        pet_name = pet.get("name", "").lower()
        pet_color = None
        tags = pet.get("tags", [])
        if tags and isinstance(tags, list):
            for tag in tags:
                if "color" in tag.get("name", "").lower():
                    pet_color = tag.get("name", "").lower()
                    break
        if species != "all" and pet_species != species.lower():
            continue
        if color and pet_color and color.lower() not in pet_color:
            continue
        if name_contains and name_contains.lower() not in pet_name:
            continue
        filtered.append(pet)
    return filtered

async def process_pet(entity: Dict[str, Any]) -> None:
    # Add a timestamp when the pet entity is processed
    entity["processedAt"] = datetime.utcnow().isoformat()

    # Add default description if missing or empty
    if not entity.get("description"):
        entity["description"] = "No description provided."

    # Example: add or update color field based on tags
    color = None
    tags = entity.get("tags", [])
    if tags and isinstance(tags, list):
        for tag in tags:
            tag_name = tag.get("name", "").lower()
            if "color" in tag_name:
                color = tag.get("name")
                break
    if color:
        entity["color"] = color
    else:
        entity.setdefault("color", None)

    # Add a secondary entity "pet_stats" for demonstration
    pet_stats = {
        "pet_id": entity.get("id"),
        "createdAt": datetime.utcnow().isoformat(),
        "healthScore": 100  # Example static value
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_stats",
            entity_version=ENTITY_VERSION,
            entity=pet_stats,
            workflow=None
        )
    except Exception as e:
        logger.error(f"Failed to add pet_stats for pet {entity.get('id')}: {e}")

@app.route("/pets/query", methods=["POST"])
@validate_request(PetsQuery)
async def query_pets(data: PetsQuery):
    species = data.species.lower()
    status = data.status.lower()
    filters = data.filters
    age_range = filters.ageRange
    color = filters.color
    name_contains = filters.nameContains

    if status not in {"available", "pending", "sold", "all"}:
        status = "available"
    statuses_to_fetch = [status] if status != "all" else ["available", "pending", "sold"]

    all_pets = []
    for st in statuses_to_fetch:
        pets = await fetch_pets_from_petstore(st)
        all_pets.extend(pets)

    filtered_pets = filter_pets(all_pets, species, age_range, color, name_contains)

    for pet in filtered_pets:
        pet_id_str = str(pet.get("id", ""))
        pet_data = pet.copy()
        pet_data["id"] = pet_id_str
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data,
                workflow=process_pet
            )
        except Exception as e:
            logger.error(f"Failed to add pet {pet_id_str} in entity service: {e}")

    def pet_to_response(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "species": pet.get("category", {}).get("name", ""),
            "age": None,
            "color": pet.get("color", None),
            "status": pet.get("status", ""),
            "description": pet.get("description", "") or ""
        }

    return jsonify({"pets": [pet_to_response(p) for p in filtered_pets]})

@app.route("/pets", methods=["GET"])
async def get_cached_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.error(f"Failed to get pets from entity service: {e}")
        pets = []

    def pet_to_response(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "species": pet.get("category", {}).get("name", ""),
            "age": None,
            "color": pet.get("color", None),
            "status": pet.get("status", ""),
            "description": pet.get("description", "") or ""
        }

    return jsonify({"pets": [pet_to_response(p) for p in pets]})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptionRequest)
async def adopt_pet(data: AdoptionRequest):
    pet_id = data.petId.strip()
    user_info = {"name": data.user.name, "email": data.user.email}

    if not pet_id or not user_info["name"] or not user_info["email"]:
        return jsonify({"success": False, "message": "Missing petId or user name/email"}), 400

    if await cache.is_adopted(pet_id):
        return jsonify({"success": False, "message": f"Pet {pet_id} is already adopted"}), 409

    success = await cache.adopt_pet(pet_id, user_info)
    if success:
        return jsonify({"success": True, "message": f"Pet {pet_id} successfully adopted by {user_info['name']}"})
    else:
        return jsonify({"success": False, "message": "Adoption failed due to unknown reason"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.error(f"Failed to get pet {pet_id} from entity service: {e}")
        return jsonify({"message": f"Pet {pet_id} not found"}), 404

    if not pet:
        return jsonify({"message": f"Pet {pet_id} not found"}), 404

    response_pet = {
        "id": str(pet.get("id", "")),
        "name": pet.get("name", ""),
        "species": pet.get("category", {}).get("name", ""),
        "age": None,
        "color": pet.get("color", None),
        "status": pet.get("status", ""),
        "description": pet.get("description", "") or ""
    }
    return jsonify(response_pet)

@app.route("/pets/funfacts", methods=["GET"])
async def fun_facts():
    return jsonify({"funFacts": FUN_FACTS})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)