```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

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

    async def update(self, key: str, update_func) -> None:
        async with self._lock:
            old_value = self._data.get(key)
            new_value = update_func(old_value)
            self._data[key] = new_value

cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper: fetch pets from Petstore API with filters
async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> list:
    # Petstore API does not support complex filtering, so we fetch all and filter manually
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    status = filters.get("status")
    params = {}
    if status:
        params['status'] = status
    else:
        params['status'] = "available"  # Default since petstore expects one of available, pending, sold

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Error fetching pets from Petstore: {e}")
        return []

    # Apply additional filters manually (type, ageRange)
    def matches_filters(pet: dict) -> bool:
        if "type" in filters and filters["type"]:
            # The Petstore API does not have a direct "type" field; it uses "category" with "name"
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type != filters["type"].lower():
                return False
        if "ageRange" in filters and filters["ageRange"]:
            # Petstore API pets don't have age info; mock skipping age filter here
            # TODO: Age filter not supported by Petstore API, ignoring
            pass
        return True

    filtered = [pet for pet in pets if matches_filters(pet)]
    return filtered


# Helper: fetch pet details by ID from Petstore API
async def fetch_pet_details_from_petstore(pet_id: int) -> Optional[Dict[str, Any]]:
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            pet = resp.json()
            # Petstore API may return a "code" and "message" on error instead of pet object
            if "code" in pet and pet["code"] != 200:
                return None
            return pet
    except Exception as e:
        logger.exception(f"Error fetching pet details from Petstore: {e}")
        return None


# Business logic: enrich pet details with fun facts and recommended toys
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

    enriched = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet_type if pet_type else None,
        "age": None,  # Petstore API has no age data
        "status": pet.get("status"),
        "description": pet.get("description"),
        "funFact": fun_facts.get(pet_type, "Pets bring joy to our lives!"),
        "recommendedToys": toys.get(pet_type, ["toy"])
    }
    return enriched


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    # Validate keys manually since no @validate_request
    filters = {
        "type": data.get("type"),
        "status": data.get("status", "available"),
        "ageRange": data.get("ageRange")
    }
    logger.info(f"Received /pets/search with filters: {filters}")

    pets = await fetch_pets_from_petstore(filters)

    # Simplify pets data for response
    def simplify_pet(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "age": None,  # No age info available
            "status": pet.get("status"),
            "description": pet.get("description")
        }

    simplified_pets = list(map(simplify_pet, pets))

    # Cache last searched pets list for GET /pets
    await cache.set("last_search_results", simplified_pets)

    return jsonify({"pets": simplified_pets})


@app.route("/pets", methods=["GET"])
async def pets_get_last_search():
    pets = await cache.get("last_search_results")
    if pets is None:
        return jsonify({"pets": []})
    return jsonify({"pets": pets})


@app.route("/pets/details", methods=["POST"])
async def pets_details():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not pet_id or not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400

    logger.info(f"Received /pets/details for petId: {pet_id}")

    pet = await fetch_pet_details_from_petstore(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404

    enriched = enrich_pet_details(pet)

    # Cache detailed pet info for GET /pets/{id}
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
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
