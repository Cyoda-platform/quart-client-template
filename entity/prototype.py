import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # validate_querystring if needed

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# dataclasses for request validation
@dataclass
class QueryFilters:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class PetId:
    petId: int

# In-memory async-safe cache
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data: Optional[Dict[str, Any]] = None

    async def set(self, data: Dict[str, Any]):
        async with self._lock:
            self._data = data

    async def get(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._data

cache = Cache()
PETSTORE_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets(filters: Dict[str, Any]) -> Dict[str, Any]:
    status = filters.get("status")
    pet_type = filters.get("type")
    name_filter = filters.get("name")
    pets = []
    async with httpx.AsyncClient() as client:
        try:
            if status:
                r = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
            else:
                for st in ["available", "pending", "sold"]:
                    r = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": st})
                    r.raise_for_status()
                    pets.extend(r.json())
        except Exception:
            logger.exception("Error fetching pets")
            raise

    def match(pet: Dict[str, Any]) -> bool:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            return False
        if name_filter and name_filter.lower() not in pet.get("name", "").lower():
            return False
        return True

    filtered = [pet for pet in pets if match(pet)]
    result = []
    for pet in filtered:
        result.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        })
    return {"pets": result}

async def fetch_pet_details(pet_id: int) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
        except httpx.HTTPStatusError:
            logger.exception(f"Pet {pet_id} not found")
            return {"error": f"Pet {pet_id} not found."}
        except Exception:
            logger.exception("Error fetching pet details")
            raise

    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag],
        "description": pet.get("description") or "",
    }

# POST /pets/query
# Workaround: validate_request must come after route for POST due to quart-schema defect
@app.route("/pets/query", methods=["POST"])
@validate_request(QueryFilters)
async def pets_query(data: QueryFilters):
    try:
        filters = data.__dict__
        pets_data = await fetch_pets(filters)
        await cache.set(pets_data)
        return jsonify(pets_data)
    except Exception:
        logger.exception("Failed /pets/query")
        return jsonify({"error": "Failed to process pets query"}), 500

# GET /pets - no validation needed
@app.route("/pets", methods=["GET"])
async def get_last_pets():
    try:
        pets_data = await cache.get()
        return jsonify(pets_data or {"pets": []})
    except Exception:
        logger.exception("Failed GET /pets")
        return jsonify({"error": "Failed to retrieve cached pets"}), 500

# POST /pets/details
# Workaround: validate_request must come after route for POST due to quart-schema defect
@app.route("/pets/details", methods=["POST"])
@validate_request(PetId)
async def pets_details(data: PetId):
    try:
        pet_details = await fetch_pet_details(data.petId)
        if "error" in pet_details:
            return jsonify(pet_details), 404
        return jsonify(pet_details)
    except Exception:
        logger.exception("Failed /pets/details")
        return jsonify({"error": "Failed to fetch pet details"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout,
                        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                        level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)