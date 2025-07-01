```python
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for pets data and last search parameters
class AsyncCache:
    def __init__(self):
        self._pets = None
        self._pets_by_id = {}
        self._lock = asyncio.Lock()

    async def set_pets(self, pets):
        async with self._lock:
            self._pets = pets
            self._pets_by_id = {p["id"]: p for p in pets}

    async def get_pets(self):
        async with self._lock:
            return self._pets

    async def get_pet_by_id(self, pet_id):
        async with self._lock:
            return self._pets_by_id.get(pet_id)

cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Fun pet facts list for POST /pets/fun-fact (no external API used)
FUN_PET_FACTS = [
    "Cats sleep for 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind themselves without turning their heads.",
    "Goldfish have a memory span of at least three months.",
    "Guinea pigs communicate using over 11 different sounds.",
]

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Accepts optional filters: type, status
    Fetches pets from Petstore API filtered by status (Petstore API supports status filter)
    Since Petstore API does not support type filtering natively, filter client-side.
    Caches results in memory.
    """
    try:
        data = await request.get_json(force=True)
        pet_type = data.get("type", None)
        status = data.get("status", None)

        async with httpx.AsyncClient() as client:
            # Petstore API supports status filter for pet findByStatus endpoint
            params = {}
            if status:
                params["status"] = status
            else:
                params["status"] = "available"  # default to available pets

            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets_raw = resp.json()

        # Filter by type client-side if requested
        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        # Normalize pets to expected response format
        pets = []
        for p in pets_filtered:
            pets.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name", None),
                "status": p.get("status"),
                "photoUrls": p.get("photoUrls", []),
            })

        await cache.set_pets(pets)

        return jsonify({"pets": pets})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets"}), 500


@app.route("/pets/fun-fact", methods=["POST"])
async def pets_fun_fact():
    """
    POST /pets/fun-fact
    Returns a random pet fact from a fixed list.
    """
    import random

    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})


@app.route("/pets", methods=["GET"])
async def get_cached_pets():
    """
    GET /pets
    Returns the last cached pets list from previous search.
    """
    pets = await cache.get_pets()
    if pets is None:
        return jsonify({"error": "No cached pets data found. Please perform a search first."}), 404
    return jsonify({"pets": pets})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_cached_pet_by_id(pet_id: int):
    """
    GET /pets/{id}
    Returns details of a specific pet from cached data.
    """
    pet = await cache.get_pet_by_id(pet_id)
    if pet is None:
        return jsonify({"error": f"Pet with id {pet_id} not found in cache."}), 404
    return jsonify(pet)


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
