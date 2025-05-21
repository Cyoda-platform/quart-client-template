import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SearchRequest:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class DetailsRequest:
    ids: List[int]

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

def add_fun_description(pet: Dict) -> Dict:
    description = f"Purrfect Pet: Meet {pet.get('name', 'our furry friend')}! Such a lovely {pet.get('type', 'pet')}."
    pet["description"] = description
    pet.setdefault("tags", [])
    if "purrfect" not in pet["tags"]:
        pet["tags"].append("purrfect")
    return pet

async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            response.raise_for_status()
            pets = response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []
    filtered = []
    for pet in pets:
        matches = True
        if filters.get("type"):
            pet_type = pet.get("category", {}).get("name", "").lower()
            if pet_type != filters["type"].lower():
                matches = False
        if filters.get("status"):
            if pet.get("status", "").lower() != filters["status"].lower():
                matches = False
        if filters.get("name"):
            if filters["name"].lower() not in pet.get("name", "").lower():
                matches = False
        if matches:
            filtered.append(pet)
    return filtered

async def fetch_pet_details_from_petstore(pet_ids: List[int]) -> List[Dict]:
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
    return results

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)  # Workaround: validate_request after route decorator due to quart-schema defect
async def pets_search(data: SearchRequest):
    filters = {"type": data.type, "status": data.status, "name": data.name}
    pets = await fetch_pets_from_petstore(filters)
    pets_with_desc = [add_fun_description(p) for p in pets]
    await cache.set_search_cache(pets_with_desc)
    return jsonify({"pets": pets_with_desc})

@app.route("/pets/details", methods=["POST"])
@validate_request(DetailsRequest)  # Workaround: validate_request after route decorator due to quart-schema defect
async def pets_details(data: DetailsRequest):
    pet_ids = data.ids
    pets = await fetch_pet_details_from_petstore(pet_ids)
    pets_with_desc = []
    for pet in pets:
        pet_enhanced = add_fun_description(pet)
        pets_with_desc.append(pet_enhanced)
        await cache.set_pet_detail(pet_enhanced.get("id"), pet_enhanced)
    return jsonify({"pets": pets_with_desc})

@app.route("/pets", methods=["GET"])
async def pets_get():
    pets = await cache.get_search_cache()
    return jsonify({"pets": pets or []})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_get(pet_id: int):
    pet = await cache.get_pet_detail(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found in cache"}), 404
    return jsonify(pet)

if __name__ == "__main__":
    import os
    if os.environ.get("DEBUG_ASYNCIO", "").lower() in ("1", "true", "yes"):
        logging.getLogger("asyncio").setLevel(logging.DEBUG)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
