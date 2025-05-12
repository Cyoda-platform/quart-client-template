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

# In-memory "database" mocks
favorites_store: Dict[int, Dict] = {}  # petId -> pet data cache

# External Petstore API base URL (Swagger Petstore public API)
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

# Sample pet facts for fun feature
PET_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Guinea pigs communicate with squeaks and purrs.",
    "Goldfish can recognize their owners."
]


async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    """
    Query the external Petstore API with filters.
    Petstore API supports querying by status only, so we will filter results locally for other fields.

    :param filters: Dict with possible keys: type, status, tags, name
    :return: List of pet dicts
    """
    status = filters.get("status", "available")
    # Petstore API: GET /pet/findByStatus?status=available
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status}

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []

    # Local filtering for type, tags, name
    filtered = []
    type_filter = filters.get("type")
    tags_filter = set(filters.get("tags", []))
    name_filter = filters.get("name", "").lower()

    for pet in pets:
        # Petstore API pet object example:
        # {
        #   "id": int,
        #   "name": str,
        #   "photoUrls": [str],
        #   "status": str,
        #   "category": {"id": int, "name": str},  # category.name is pet type
        #   "tags": [{"id": int, "name": str}]
        # }

        pet_type = pet.get("category", {}).get("name")
        if type_filter and (not pet_type or pet_type.lower() != type_filter.lower()):
            continue

        if tags_filter:
            pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
            if not tags_filter.issubset(pet_tags):
                continue

        if name_filter and name_filter not in pet.get("name", "").lower():
            continue

        # Normalize response fields to match API spec
        filtered.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet_type,
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", [])],
                "photoUrls": pet.get("photoUrls", []),
            }
        )
    return filtered


@app.route("/pets/query", methods=["POST"])
async def pets_query():
    data = await request.get_json(force=True)
    # Fire and forget processing pattern is not essential here since this endpoint returns immediately
    pets = await fetch_pets_from_petstore(data or {})
    return jsonify({"pets": pets})


@app.route("/favorites/add", methods=["POST"])
async def favorites_add():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not pet_id or not isinstance(pet_id, int):
        return jsonify({"success": False, "message": "Invalid or missing petId."}), 400

    # Check if we already have pet cached, else try to fetch it (simplified)
    pet = favorites_store.get(pet_id)
    if not pet:
        # TODO: Could fetch pet details from Petstore API /pet/{petId} here, but Petstore API has limited support
        # For prototype, try to fetch from available pets
        pets = await fetch_pets_from_petstore({"status": "available"})
        pet = next((p for p in pets if p["id"] == pet_id), None)
        if not pet:
            return jsonify({"success": False, "message": "Pet not found."}), 404
        favorites_store[pet_id] = pet
    else:
        logger.info(f"Pet {pet_id} already in favorites cache")

    return jsonify({"success": True, "message": "Pet added to favorites."})


@app.route("/favorites", methods=["GET"])
async def favorites_list():
    # Return list of favorite pets from local cache
    return jsonify({"favorites": list(favorites_store.values())})


@app.route("/fun/random-fact", methods=["POST"])
async def fun_random_fact():
    import random

    fact = random.choice(PET_FACTS)
    return jsonify({"fact": fact})


if __name__ == "__main__":
    import sys

    # Setup basic logging to stdout
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
