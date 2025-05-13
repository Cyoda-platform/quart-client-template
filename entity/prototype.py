```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "persistence" cache (async-safe by design of Quart's event loop)
pets_cache: Dict[int, Dict[str, Any]] = {}
pet_id_seq = 1  # local sequence for new pet IDs


# --- Helpers ---

async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> list:
    """
    Call Petstore API to search pets. 
    Petstore Swagger: https://petstore.swagger.io/#/pet/findPetsByStatus
    We will call /pet/findByStatus with status filter (if any).
    If type filter is provided, filter locally by type.
    """
    status = filters.get("status")
    pet_type = filters.get("type")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Petstore API supports only 'status' filter on findByStatus endpoint
            statuses = [status] if status else ["available", "pending", "sold"]
            response = await client.get(
                "https://petstore.swagger.io/v2/pet/findByStatus",
                params={"status": ",".join(statuses)},
            )
            response.raise_for_status()
            pets = response.json()

            # Filter locally by type if given
            if pet_type:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
    except Exception as e:
        logger.exception(e)
        return []


async def add_pet_to_petstore(pet_data: Dict[str, Any]) -> int:
    """
    Call Petstore API to add a new pet.
    POST /pet expects full pet object with id, category, etc.
    We'll generate a random id locally (not perfect but prototype).
    """
    global pet_id_seq

    # Petstore requires id and category object
    pet_id = None
    try:
        # Assign pet id sequentially in prototype
        pet_id = pet_id_seq
        # Increment sequence
        # NOTE: This is not async safe in real apps; okay for prototype
        globals()["pet_id_seq"] += 1  

        body = {
            "id": pet_id,
            "name": pet_data["name"],
            "photoUrls": pet_data.get("photoUrls", []),
            "status": pet_data.get("status", "available"),
            "category": {"id": 0, "name": pet_data.get("type", "unknown")},
            "tags": [],
        }

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post("https://petstore.swagger.io/v2/pet", json=body)
            r.raise_for_status()

        # Store locally as well
        pets_cache[pet_id] = {
            "id": pet_id,
            "name": pet_data["name"],
            "type": pet_data.get("type", ""),
            "status": pet_data.get("status", "available"),
            "photoUrls": pet_data.get("photoUrls", []),
        }
        return pet_id
    except Exception as e:
        logger.exception(e)
        raise e


async def get_pet_from_cache(pet_id: int) -> Dict[str, Any]:
    """Retrieve pet details from local cache (mock persistence)."""
    return pets_cache.get(pet_id)


async def get_random_pet_joke() -> str:
    """
    Get a fun pet joke.
    Using https://official-joke-api.appspot.com/jokes/animal/random
    Fallback to static joke on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://official-joke-api.appspot.com/jokes/animal/random")
            r.raise_for_status()
            jokes = r.json()
            if jokes and isinstance(jokes, list):
                joke_obj = jokes[0]
                return f"{joke_obj.get('setup', '')} {joke_obj.get('punchline', '')}".strip()
    except Exception as e:
        logger.exception(e)

    # TODO: Replace with better fallback or joke source if needed
    return "Why don't cats play poker in the jungle? Too many cheetahs!"


# --- Routes ---

@app.route("/pets/search", methods=["POST"])
async def search_pets():
    data = await request.get_json(force=True)
    pets = await fetch_pets_from_petstore(data or {})
    # Normalize response format per spec
    response_pets = []
    for pet in pets:
        response_pets.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", "") if pet.get("category") else "",
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        })
    return jsonify({"pets": response_pets})


@app.route("/pets/add", methods=["POST"])
async def add_pet():
    data = await request.get_json(force=True)
    try:
        pet_id = await add_pet_to_petstore(data)
        return jsonify({"success": True, "petId": pet_id})
    except Exception:
        # Exception already logged in helper
        return jsonify({"success": False}), 500


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = await get_pet_from_cache(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/joke", methods=["POST"])
async def pet_joke():
    joke = await get_random_pet_joke()
    return jsonify({"joke": joke})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
