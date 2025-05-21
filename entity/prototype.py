```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache simulation (per app instance)
class AsyncCache:
    def __init__(self):
        self._pets_search_cache: Optional[List[Dict]] = None
        self._pets_details_cache: Dict[int, Dict] = {}

    async def get_search_cache(self) -> Optional[List[Dict]]:
        return self._pets_search_cache

    async def set_search_cache(self, pets: List[Dict]):
        self._pets_search_cache = pets

    async def get_pet_detail(self, pet_id: int) -> Optional[Dict]:
        return self._pets_details_cache.get(pet_id)

    async def set_pet_detail(self, pet_id: int, detail: Dict):
        self._pets_details_cache[pet_id] = detail


cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utils

def add_fun_description(pet: Dict) -> Dict:
    # Add a fun/custom description/tag to the pet data
    description = f"Purrfect Pet: Meet {pet.get('name', 'our furry friend')}! Such a lovely {pet.get('type', 'pet')}."
    pet["description"] = description
    pet.setdefault("tags", [])
    if "purrfect" not in pet["tags"]:
        pet["tags"].append("purrfect")
    return pet


async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    """
    Fetch pets from external Petstore API using filters.
    Petstore API doesn't support direct filtering, so we fetch all and filter ourselves.
    TODO: If Petstore API supports filtering in future, replace with direct filtered request.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            response.raise_for_status()
            pets = response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []

    # Filtering locally based on filters in POST /pets/search
    filtered = []
    for pet in pets:
        matches = True
        if "type" in filters and filters["type"]:
            # Petstore API pet type is from pet['category']['name'], but might be missing
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type != filters["type"].lower():
                matches = False
        if "status" in filters and filters["status"]:
            if pet.get("status", "").lower() != filters["status"].lower():
                matches = False
        if "name" in filters and filters["name"]:
            if filters["name"].lower() not in pet.get("name", "").lower():
                matches = False
        if matches:
            filtered.append(pet)
    return filtered


async def fetch_pet_details_from_petstore(pet_ids: List[int]) -> List[Dict]:
    """
    Fetch pet details by IDs from Petstore API.
    Multiple IDs require multiple calls as Petstore API doesn't support batch fetch.
    """
    results = []
    async with httpx.AsyncClient() as client:
        for pet_id in pet_ids:
            try:
                response = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                response.raise_for_status()
                pet = response.json()
                results.append(pet)
            except Exception as e:
                logger.exception(f"Failed to fetch pet details for ID {pet_id}: {e}")
                # Skip missing or error pets
    return results


# Routes

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    - Request: JSON with optional filters: type, status, name
    - Calls external Petstore API to get pets, filters locally.
    - Adds fun description.
    - Caches the results.
    - Returns filtered pets list.
    """
    data = await request.get_json(force=True)
    filters = {
        "type": data.get("type"),
        "status": data.get("status"),
        "name": data.get("name"),
    }

    pets = await fetch_pets_from_petstore(filters)
    pets_with_desc = [add_fun_description(pet) for pet in pets]
    await cache.set_search_cache(pets_with_desc)

    return jsonify({"pets": pets_with_desc})


@app.route("/pets/details", methods=["POST"])
async def pets_details():
    """
    POST /pets/details
    - Request: JSON {"ids": [int, int, ...]}
    - Calls external Petstore API to get details for each pet id.
    - Adds fun description.
    - Caches each pet detail.
    - Returns list of pet details.
    """
    data = await request.get_json(force=True)
    pet_ids = data.get("ids", [])
    if not isinstance(pet_ids, list) or not all(isinstance(i, int) for i in pet_ids):
        return jsonify({"error": "Invalid 'ids' list"}), 400

    pets = await fetch_pet_details_from_petstore(pet_ids)
    pets_with_desc = []
    for pet in pets:
        pet_enhanced = add_fun_description(pet)
        pets_with_desc.append(pet_enhanced)
        # Cache individually
        await cache.set_pet_detail(pet_enhanced.get("id"), pet_enhanced)

    return jsonify({"pets": pets_with_desc})


@app.route("/pets", methods=["GET"])
async def pets_get():
    """
    GET /pets
    - Returns last cached pet list from /pets/search
    - No external calls.
    """
    pets = await cache.get_search_cache()
    if pets is None:
        return jsonify({"pets": []})
    return jsonify({"pets": pets})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_get(pet_id: int):
    """
    GET /pets/{petId}
    - Returns cached pet details by ID.
    - No external calls.
    - 404 if not found.
    """
    pet = await cache.get_pet_detail(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found in cache"}), 404
    return jsonify(pet)


if __name__ == "__main__":
    import os

    # Enable asyncio debug logging if environment variable is set
    if os.environ.get("DEBUG_ASYNCIO", "").lower() in ("1", "true", "yes"):
        logging.getLogger("asyncio").setLevel(logging.DEBUG)

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
