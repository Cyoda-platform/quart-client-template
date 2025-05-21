import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class PetsQuery:
    filter: Dict[str, Any]

@dataclass
class FunFactRequest:
    category: Optional[str] = None

# Local in-memory cache to mock persistence
class AsyncCache:
    def __init__(self):
        self._data = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._data[key] = value

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return self._data.get(key)

    async def clear(self, key: str):
        async with self._lock:
            if key in self._data:
                del self._data[key]

cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
FUN_PET_FACTS = [
    "Cats have five toes on their front paws, but only four toes on their back paws.",
    "Dogs have about 1,700 taste buds.",
    "Rabbits can see nearly 360 degrees at once.",
    "Guinea pigs communicate through a variety of sounds including purring.",
    "Goldfish have a memory span of at least three months."
]

async def fetch_pets_from_petstore(filter_params: Dict[str, Any]) -> Dict[str, Any]:
    status = filter_params.get("status", "available")
    category_filter = filter_params.get("category")
    tags_filter = set(filter_params.get("tags") or [])

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(e)
            return {"pets": [], "count": 0}

    def pet_matches(pet: Dict[str, Any]) -> bool:
        if category_filter:
            cat = pet.get("category")
            if not cat or cat.get("name") != category_filter:
                return False
        if tags_filter:
            pet_tags = {t.get("name") for t in pet.get("tags", []) if t.get("name")}
            if not tags_filter.issubset(pet_tags):
                return False
        return True

    filtered_pets = [pet for pet in pets if pet_matches(pet)]
    pets_response = []
    for pet in filtered_pets:
        pets_response.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "category": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "tags": [t.get("name") for t in pet.get("tags", []) if t.get("name")]
        })

    return {"pets": pets_response, "count": len(pets_response)}

async def generate_fun_fact(category: Optional[str] = None) -> str:
    import random
    return random.choice(FUN_PET_FACTS)  # TODO: fetch from external source if needed

@app.route("/pets/query", methods=["POST"])
# issue workaround: validate_request must go after route decorator for POST
@validate_request(PetsQuery)
async def pets_query(data: PetsQuery):
    filter_params = data.filter or {}
    requested_at = datetime.utcnow().isoformat()
    await cache.set("last_pets_query", {"status": "processing", "requestedAt": requested_at})

    async def process_query():
        try:
            pets_data = await fetch_pets_from_petstore(filter_params)
            await cache.set("last_pets_query", {"status": "completed", "requestedAt": requested_at, "result": pets_data})
        except Exception as e:
            logger.exception(e)
            await cache.set("last_pets_query", {"status": "failed", "requestedAt": requested_at, "error": str(e)})

    asyncio.create_task(process_query())
    return jsonify({"message": "Pet query processing started", "requestedAt": requested_at}), 202

@app.route("/pets", methods=["GET"])
async def pets_get():
    last_query = await cache.get("last_pets_query")
    if not last_query:
        return jsonify({"message": "No pet query found"}), 404
    if last_query.get("status") != "completed":
        return jsonify({"message": f"Pet query status: {last_query.get('status')}"}), 202
    result = last_query.get("result", {"pets": [], "count": 0})
    return jsonify(result)

@app.route("/pets/funfact", methods=["POST"])
# issue workaround: validate_request must go after route decorator for POST
@validate_request(FunFactRequest)
async def pets_funfact_post(data: FunFactRequest):
    category = data.category
    requested_at = datetime.utcnow().isoformat()

    async def process_funfact():
        try:
            fact = await generate_fun_fact(category)
            await cache.set("last_funfact", {"requestedAt": requested_at, "fact": fact})
        except Exception as e:
            logger.exception(e)
            await cache.set("last_funfact", {"requestedAt": requested_at, "fact": None, "error": str(e)})

    asyncio.create_task(process_funfact())
    return jsonify({"message": "Fun fact generation started", "requestedAt": requested_at}), 202

@app.route("/pets/funfact", methods=["GET"])
async def pets_funfact_get():
    last_fact = await cache.get("last_funfact")
    if not last_fact or not last_fact.get("fact"):
        return jsonify({"message": "No fun fact found"}), 404
    return jsonify({"fact": last_fact["fact"]})

if __name__ == '__main__':
    import sys
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)