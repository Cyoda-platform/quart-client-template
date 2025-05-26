import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# dataclasses for request validation
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

# In-memory cache to hold last query results and adoption status
class InMemoryCache:
    def __init__(self):
        self._pets_cache: Optional[List[Dict[str, Any]]] = None
        self._adoptions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def set_pets(self, pets: List[Dict[str, Any]]):
        async with self._lock:
            self._pets_cache = pets

    async def get_pets(self) -> Optional[List[Dict[str, Any]]]:
        async with self._lock:
            return self._pets_cache

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

@app.route("/pets/query", methods=["POST"])
@validate_request(PetsQuery)  # workaround: validate_request defect requires this order for POST
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
    await cache.set_pets(filtered_pets)

    def pet_to_response(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "species": pet.get("category", {}).get("name", ""),
            "age": None,  # TODO: Petstore API does not provide age
            "color": None,  # No reliable color info in API; skipped
            "status": pet.get("status", ""),
            "description": pet.get("description", "") or ""
        }

    response_pets = [pet_to_response(p) for p in filtered_pets]
    return jsonify({"pets": response_pets})

@app.route("/pets", methods=["GET"])
async def get_cached_pets():
    pets = await cache.get_pets()
    if pets is None:
        return jsonify({"pets": []})
    def pet_to_response(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "species": pet.get("category", {}).get("name", ""),
            "age": None,
            "color": None,
            "status": pet.get("status", ""),
            "description": pet.get("description", "") or ""
        }
    response_pets = [pet_to_response(p) for p in pets]
    return jsonify({"pets": response_pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptionRequest)  # workaround: validate_request defect requires this order for POST
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

@app.route("/pets/funfacts", methods=["GET"])
async def fun_facts():
    return jsonify({"funFacts": FUN_FACTS})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)