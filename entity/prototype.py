import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# request data models
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
    petId: int

# Simple in-memory async-safe cache using asyncio.Lock
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
        if filters.get("ageRange"):
            # TODO: Age filter not supported by Petstore API, ignoring
            pass
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
    pet_type = pet.get("category", {}).get("name", "").lower()
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
        "type": pet_type or None,
        "age": None,
        "status": pet.get("status"),
        "description": pet.get("description"),
        "funFact": fun_facts.get(pet_type, "Pets bring joy to our lives!"),
        "recommendedToys": toys.get(pet_type, ["toy"])
    }

# POST first, then validate_request -> workaround for validate_request defect
@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPets)
async def pets_search(data: SearchPets):
    filters = {
        "type": data.type,
        "status": data.status or "available",
        "ageRange": {"min": data.ageRange.min, "max": data.ageRange.max} if data.ageRange else None
    }
    logger.info(f"Received /pets/search with filters: {filters}")
    pets = await fetch_pets_from_petstore(filters)
    def simplify_pet(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
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

# POST first, then validate_request -> workaround for validate_request defect
@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_id = data.petId
    logger.info(f"Received /pets/details for petId: {pet_id}")
    pet = await fetch_pet_details_from_petstore(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    enriched = enrich_pet_details(pet)
    await cache.set(f"pet_details_{pet_id}", enriched)
    return jsonify(enriched)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get_details(pet_id: int):
    pet = await cache.get(f"pet_details_{pet_id}")
    if pet is None:
        return jsonify({"error": "Pet details not cached. Please POST /pets/details first."}), 404
    return jsonify(pet)

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)