```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

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

# Instantiate caches
search_cache = AsyncCache()
adoption_cache = AsyncCache()

# External Petstore API base URL
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_external(type_filter=None, status_filter=None):
    # Build query params for pet status and type
    # Petstore API /pet/findByStatus?status=available,sold,pending
    # No direct "type" filter in Petstore API, so we filter client-side.

    params = {}
    if status_filter:
        # Petstore expects comma-separated statuses
        params["status"] = status_filter

    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            # Filter by type if provided (case-insensitive)
            if type_filter:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_filter.lower()]
            return pets
        except Exception as e:
            logger.exception("Failed to fetch pets from external Petstore API")
            return []

async def process_pets_search(search_id, filters):
    # Fetch pets from external API
    type_filter = filters.get("type")
    status_filter = filters.get("status")
    fun_filter = filters.get("fun_filter")

    pets = await fetch_pets_external(type_filter, status_filter)

    # Apply fun business logic - example: "purrfect_match" filter returns only cats with "purr" in name
    if fun_filter == "purrfect_match":
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == "cat" and 
                "purr" in p.get("name", "").lower()]

    # Simplify pets for response & storage
    simplified_pets = []
    for p in pets:
        simplified_pets.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name", ""),
            "status": p.get("status"),
            "description": p.get("tags")[0]["name"] if p.get("tags") else ""
        })

    result = {
        "search_id": search_id,
        "pets": simplified_pets,
        "result_count": len(simplified_pets),
        "created_at": datetime.utcnow().isoformat()
    }

    await search_cache.set(search_id, result)

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    search_id = str(uuid.uuid4())
    # Store initial processing state (optional)
    await search_cache.set(search_id, {"status": "processing", "created_at": datetime.utcnow().isoformat()})

    # Fire and forget processing task
    asyncio.create_task(process_pets_search(search_id, data))

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
    # If still processing
    if result.get("status") == "processing":
        return jsonify({"search_id": search_id, "status": "processing"}), 202
    return jsonify({
        "search_id": search_id,
        "pets": result.get("pets", [])
    })

async def process_adoption_request(adoption_id, data):
    # TODO: Add real validation, checks, or external calls if needed.
    # For prototype, we simulate processing delay and approve all.
    await asyncio.sleep(2)  # Simulate processing delay
    adoption_record = {
        "adoption_id": adoption_id,
        "pet_id": data["pet_id"],
        "adopter_name": data["adopter_name"],
        "adopter_contact": data["adopter_contact"],
        "status": "approved",
        "created_at": datetime.utcnow().isoformat()
    }
    await adoption_cache.set(adoption_id, adoption_record)

@app.route("/pets/adopt", methods=["POST"])
async def adopt_pet():
    data = await request.get_json(force=True)
    # Minimal required fields check
    if not all(k in data for k in ("pet_id", "adopter_name", "adopter_contact")):
        return jsonify({"error": "Missing required adoption fields."}), 400

    adoption_id = str(uuid.uuid4())
    # Mark as pending initially
    await adoption_cache.set(adoption_id, {
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        **data
    })

    # Fire and forget processing
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
```