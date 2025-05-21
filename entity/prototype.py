```python
import asyncio
import logging
import random
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for pets keyed by pet id: {id: pet_data}
pets_cache = {}

# Fun facts for pets - simple static data for prototype
FUN_FACTS = {
    "cat": [
        "Cats sleep 70% of their lives.",
        "A group of cats is called a clowder.",
        "Cats have five toes on their front paws, but only four toes on their back paws."
    ],
    "dog": [
        "Dogs have three eyelids.",
        "Dogs’ sense of smell is about 40 times better than humans'.",
        "Dogs can learn more than 1000 words."
    ],
    "default": [
        "Pets bring joy and companionship to humans.",
        "Playing with pets can reduce stress and anxiety."
    ]
}

PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Async HTTP client instance for reuse
async_client = httpx.AsyncClient(timeout=10)


async def fetch_pets_from_petstore(params: dict):
    """
    Fetch pets from Petstore API by status or type filter.
    Petstore API supports GET /pet/findByStatus?status=available,sold,pending
    or GET /pet/findByTags?tags=tag1,tag2 but tags not relevant here.

    We'll use /pet/findByStatus as base, then filter locally by type/name if provided.
    """
    status = params.get("status", "available")
    try:
        # Petstore expects comma-separated statuses, we only support one for simplicity
        r = await async_client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
        r.raise_for_status()
        pets = r.json()
        # Filter by type and name locally
        filtered = []
        type_filter = params.get("type", "").lower()
        name_filter = params.get("name", "").lower()
        for pet in pets:
            pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
            pet_name = pet.get("name", "").lower()
            if type_filter and pet_type != type_filter:
                continue
            if name_filter and name_filter not in pet_name:
                continue
            filtered.append({
                "id": pet["id"],
                "name": pet.get("name", ""),
                "type": pet_type,
                "status": pet.get("status", ""),
                "photoUrls": pet.get("photoUrls", [])
            })
            # Cache pet for GET /pets/{id}
            pets_cache[pet["id"]] = filtered[-1]
        return filtered
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_pet_by_id_from_cache(pet_id: int):
    """
    Return pet data from cache or None if not found.
    """
    return pets_cache.get(pet_id)


async def fetch_random_pet(type_filter: str = None):
    """
    Fetch a random pet by:
    - Getting pets filtered by type and status=available from Petstore API
    - Select one randomly or None if empty
    """
    params = {"status": "available"}
    if type_filter:
        params["type"] = type_filter
    pets = await fetch_pets_from_petstore(params)
    if pets:
        pet = random.choice(pets)
        return pet
    return None


def get_fun_fact(pet_type: str = None):
    """
    Return a fun fact string based on pet_type or default.
    """
    pet_type = (pet_type or "").lower()
    facts = FUN_FACTS.get(pet_type) or FUN_FACTS["default"]
    return random.choice(facts)


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True, silent=True) or {}
    pets = await fetch_pets_from_petstore(data)
    return jsonify({"pets": pets})


@app.route("/pets/random", methods=["POST"])
async def pets_random():
    data = await request.get_json(force=True, silent=True) or {}
    pet_type = data.get("type")
    pet = await fetch_random_pet(pet_type)
    if pet:
        return jsonify({"pet": pet})
    return jsonify({"pet": None}), 404


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get(pet_id):
    pet = await fetch_pet_by_id_from_cache(pet_id)
    if pet:
        return jsonify(pet)
    return jsonify({"message": "Pet not found in cache. Please search first."}), 404


@app.route("/pets/funfact", methods=["POST"])
async def pets_funfact():
    data = await request.get_json(force=True, silent=True) or {}
    pet_type = data.get("type")
    fact = get_fun_fact(pet_type)
    return jsonify({"fact": fact})


@app.before_serving
async def startup():
    logger.info("Starting up async http client")


@app.after_serving
async def shutdown():
    await async_client.aclose()
    logger.info("Closed async http client")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
