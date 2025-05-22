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

# In-memory async-safe caches using asyncio.Lock for concurrency control
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._store = {}

    async def set(self, key, value):
        async with self._lock:
            self._store[key] = value

    async def get(self, key):
        async with self._lock:
            return self._store.get(key)

    async def update(self, key, update_dict):
        async with self._lock:
            if key in self._store:
                self._store[key].update(update_dict)
                return True
            return False

# Caches to hold search results and pets added/updated locally
search_cache = AsyncCache()
pet_cache = AsyncCache()
pet_id_seq = asyncio.Lock()
pet_id_counter = 0


async def generate_pet_id():
    global pet_id_counter
    async with pet_id_seq:
        pet_id_counter += 1
        return pet_id_counter


# Petstore API base url
PETSTORE_BASE = "https://petstore.swagger.io/v2"


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Accepts optional 'type' and 'status' to query Petstore API.
    Stores results internally with a searchId for later retrieval.
    """
    data = await request.get_json() or {}
    pet_type = data.get("type")
    status = data.get("status")

    # Build Petstore API query parameters
    params = {}
    if status:
        params["status"] = status
    # Petstore API does not support filter by type directly in findByStatus
    # TODO: Petstore API lacks direct filtering by type; we'll filter results client-side.

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Use findByStatus endpoint if status provided, else GET all pets is not available
            if status:
                resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params=params)
                resp.raise_for_status()
                pets_raw = resp.json()
            else:
                # Fallback: get pets by 'available' status if no status provided (common default)
                resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": "available"})
                resp.raise_for_status()
                pets_raw = resp.json()

        # Filter by type if provided
        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        # Normalize pets data for response and storage
        pets = []
        for p in pets_filtered:
            pets.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name", "unknown"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")] if p.get("tags") else []
            })

        search_id = str(uuid.uuid4())
        await search_cache.set(search_id, pets)
        logger.info(f"Stored search results under searchId={search_id} count={len(pets)}")

        return jsonify({"searchId": search_id})

    except httpx.HTTPError as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets from Petstore API"}), 502


@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    """
    GET /pets/search/{searchId}
    Return cached search results for given searchId.
    """
    pets = await search_cache.get(search_id)
    if pets is None:
        return jsonify({"error": "searchId not found"}), 404
    return jsonify({"pets": pets})


@app.route("/pets/add", methods=["POST"])
async def add_pet():
    """
    POST /pets/add
    Add a new pet locally (simulate adding to Petstore).
    """
    data = await request.get_json() or {}

    name = data.get("name")
    pet_type = data.get("type")
    status = data.get("status")
    tags = data.get("tags") or []

    if not name or not pet_type or not status:
        return jsonify({"error": "Missing required fields: name, type, status"}), 400

    pet_id = await generate_pet_id()
    pet_data = {
        "id": pet_id,
        "name": name,
        "type": pet_type,
        "status": status,
        "tags": tags,
    }

    await pet_cache.set(pet_id, pet_data)

    message = f"🐾 Purrfect! Pet '{name}' with ID {pet_id} has been added to your collection! 🐱"
    logger.info(f"Added new pet: {pet_data}")

    return jsonify({"petId": pet_id, "message": message})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    """
    GET /pets/{petId}
    Retrieve pet details from local store.
    """
    pet = await pet_cache.get(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/update/<int:pet_id>", methods=["POST"])
async def update_pet(pet_id):
    """
    POST /pets/update/{petId}
    Update pet details locally.
    """
    updates = await request.get_json() or {}

    allowed_fields = {"name", "status", "tags"}
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    updated = await pet_cache.update(pet_id, update_data)
    if not updated:
        return jsonify({"error": "Pet not found"}), 404

    message = f"🐾 Pet ID {pet_id} updated with love and care! 💖"
    logger.info(f"Updated pet {pet_id} with {update_data}")

    return jsonify({"message": message})


if __name__ == '__main__':
    import sys
    import logging.config

    # Simple console logging config
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s',
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
