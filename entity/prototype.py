import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request models
@dataclass
class FetchPetsRequest:
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: Optional[int] = None

@dataclass
class SearchPetsRequest:
    query: str
    status: Optional[str] = None

# Local in-memory cache for pets data
pets_cache: Dict[int, Dict] = {}
pets_cache_lock = asyncio.Lock()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

def convert_petstore_pet(pet: dict) -> dict:
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "category": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
    }

async def fetch_pets_from_petstore(
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[dict]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore: {e}")
            return []

    if tags:
        pets = [
            pet for pet in pets
            if pet.get("tags") and any(t.get("name") in tags for t in pet["tags"])
        ]
    if limit is not None:
        pets = pets[:limit]

    return [convert_petstore_pet(p) for p in pets]

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # Workaround: validation last due to validate_request defect
async def pets_fetch(data: FetchPetsRequest):
    status = data.status
    tags = data.tags
    limit = data.limit

    pets = await fetch_pets_from_petstore(status=status, tags=tags, limit=limit)
    async with pets_cache_lock:
        for pet in pets:
            pets_cache[pet["id"]] = pet

    return jsonify({"fetched": len(pets), "pets": pets})

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPetsRequest)  # Workaround: validation last due to validate_request defect
async def pets_search(data: SearchPetsRequest):
    query = data.query.strip().lower()
    status_filter = data.status

    async with pets_cache_lock:
        pets_list = list(pets_cache.values())

    def match(pet: dict) -> bool:
        if status_filter and pet.get("status") != status_filter:
            return False
        if query:
            name = pet.get("name", "").lower()
            category = pet.get("category", "").lower() if pet.get("category") else ""
            return query in name or query in category
        return True

    results = [pet for pet in pets_list if match(pet)]
    return jsonify({"results": results})

@app.route("/pets", methods=["GET"])
async def pets_get_all():
    async with pets_cache_lock:
        pets_list = list(pets_cache.values())
    return jsonify({"pets": pets_list})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get_by_id(pet_id: int):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)