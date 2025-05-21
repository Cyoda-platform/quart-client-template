import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schemas
@dataclass
class SearchRequest:
    type: str = None
    status: str = None
    fun_filter: str = None

@dataclass
class AdoptRequest:
    pet_id: int
    adopter_name: str
    adopter_contact: str

# In-memory async-safe storage using asyncio.Lock
class AsyncCache:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()

    async def set(self, key, value):
        async with self._lock:
            self._cache[key] = value

    async def get(self, key):
        async with self._lock:
            return self._cache.get(key)

search_cache = AsyncCache()
adoption_cache = AsyncCache()

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_external(type_filter=None, status_filter=None):
    params = {}
    if status_filter:
        params["status"] = status_filter
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if type_filter:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_filter.lower()]
            return pets
        except Exception:
            logger.exception("Failed to fetch pets from external Petstore API")
            return []

async def process_pets_search(search_id, filters):
    type_filter = filters.get("type")
    status_filter = filters.get("status")
    fun_filter = filters.get("fun_filter")

    pets = await fetch_pets_external(type_filter, status_filter)
    if fun_filter == "purrfect_match":
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == "cat" and 
                "purr" in p.get("name", "").lower()]

    simplified = []
    for p in pets:
        simplified.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name", ""),
            "status": p.get("status"),
            "description": p.get("tags")[0]["name"] if p.get("tags") else ""
        })

    result = {
        "search_id": search_id,
        "pets": simplified,
        "result_count": len(simplified),
        "created_at": datetime.utcnow().isoformat()
    }
    await search_cache.set(search_id, result)

@app.route("/pets/search", methods=["POST"])
# workaround: validate_request must be placed after route due to quart-schema defect
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    search_id = str(uuid.uuid4())
    await search_cache.set(search_id, {"status": "processing", "created_at": datetime.utcnow().isoformat()})
    asyncio.create_task(process_pets_search(search_id, data.__dict__))
    return jsonify({
        "search_id": search_id,
        "result_count": 0,
        "message": "Pets fetch and processing started."
    })

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    result = await search_cache.get(search_id)
    if not result:
        return jsonify({"error": "Search ID not found."}), 404
    if result.get("status") == "processing":
        return jsonify({"search_id": search_id, "status": "processing"}), 202
    return jsonify({
        "search_id": search_id,
        "pets": result.get("pets", [])
    })

async def process_adoption_request(adoption_id, data):
    await asyncio.sleep(2)  # simulate processing delay
    record = {
        "adoption_id": adoption_id,
        "pet_id": data.pet_id,
        "adopter_name": data.adopter_name,
        "adopter_contact": data.adopter_contact,
        "status": "approved",
        "created_at": datetime.utcnow().isoformat()
    }
    await adoption_cache.set(adoption_id, record)

@app.route("/pets/adopt", methods=["POST"])
# workaround: validate_request must be placed after route due to quart-schema defect
@validate_request(AdoptRequest)
async def adopt_pet(data: AdoptRequest):
    adoption_id = str(uuid.uuid4())
    await adoption_cache.set(adoption_id, {
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "pet_id": data.pet_id,
        "adopter_name": data.adopter_name,
        "adopter_contact": data.adopter_contact
    })
    asyncio.create_task(process_adoption_request(adoption_id, data))
    return jsonify({
        "adoption_id": adoption_id,
        "status": "pending",
        "message": "Adoption request received."
    })

@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption_status(adoption_id):
    record = await adoption_cache.get(adoption_id)
    if not record:
        return jsonify({"error": "Adoption ID not found."}), 404
    return jsonify({
        "adoption_id": adoption_id,
        "pet_id": record.get("pet_id"),
        "adopter_name": record.get("adopter_name"),
        "status": record.get("status")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)