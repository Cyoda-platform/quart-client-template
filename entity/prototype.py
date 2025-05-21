```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for favorites (simulate persistence)
# Use a dict keyed by pet id to store pet info
favorites_cache: Dict[int, Dict] = {}

# Static random pet facts (could be extended or fetched externally)
RANDOM_FACTS = [
    "Cats sleep for 70% of their lives.",
    "A group of cats is called a clowder.",
    "Cats have over 20 muscles that control their ears.",
    "Adult cats only meow to communicate with humans.",
    "Cats can make over 100 different sounds.",
]


async def fetch_petstore_pets() -> List[Dict]:
    """
    Fetch all pets from the Petstore API.
    Petstore Swagger URL: https://petstore.swagger.io/v2/pet/findByStatus?status=available
    """
    url = "https://petstore.swagger.io/v2/pet/findByStatus?status=available"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
            return pets
        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            return []


def filter_pets(pets: List[Dict], pet_type: Optional[str], name: Optional[str]) -> List[Dict]:
    filtered = []
    pet_type_lower = pet_type.lower() if pet_type else None
    name_lower = name.lower() if name else None

    for pet in pets:
        # Petstore API pet structure:
        # id: int, name: str, category: {id:int, name:str}, status: str, photoUrls: [], tags: [], etc.
        p_name = pet.get("name", "")
        category = pet.get("category") or {}
        p_type = category.get("name", "")

        # Filtering by type and/or name
        if pet_type_lower and pet_type_lower != p_type.lower():
            continue
        if name_lower and name_lower not in p_name.lower():
            continue

        # Map to our simplified pet structure
        filtered.append({
            "id": pet.get("id"),
            "name": p_name,
            "type": p_type,
            # Petstore does not have age or description, so we add placeholders
            "age": None,  # TODO: No age info in Petstore API
            "description": None,  # TODO: No description in Petstore API
        })

    return filtered


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    name = data.get("name")

    logger.info(f"Searching pets with type={pet_type} and name={name}")

    pets = await fetch_petstore_pets()
    filtered = filter_pets(pets, pet_type, name)

    return jsonify({"pets": filtered})


@app.route("/pets/random-fact", methods=["POST"])
async def random_fact():
    # Return one random fact from the list
    import random

    fact = random.choice(RANDOM_FACTS)
    logger.info(f"Returned random fact: {fact}")
    return jsonify({"fact": fact})


@app.route("/pets/favorites", methods=["GET"])
async def get_favorites():
    # Return list of favorited pets from local cache
    favorites_list = list(favorites_cache.values())
    logger.info(f"Returning {len(favorites_list)} favorite pets")
    return jsonify({"favorites": favorites_list})


@app.route("/pets/favorites/add", methods=["POST"])
async def add_favorite():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if pet_id is None:
        return jsonify({"success": False, "message": "Missing pet id"}), 400

    # Check if already added
    if pet_id in favorites_cache:
        return jsonify({"success": True, "message": "Pet already in favorites."})

    # Fetch pet info from Petstore API by id
    # Petstore API: GET /pet/{petId}
    url = f"https://petstore.swagger.io/v2/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pet id {pet_id} from Petstore API")
            return jsonify({"success": False, "message": "Pet not found or external API error"}), 404

    # Map pet to local simplified structure
    category = pet.get("category") or {}
    pet_info = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": category.get("name"),
        "age": None,  # TODO: no age info in Petstore API
    }

    favorites_cache[pet_id] = pet_info
    logger.info(f"Added pet id {pet_id} to favorites")
    return jsonify({"success": True, "message": "Pet added to favorites."})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
