```python
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory caches / mocks
favorite_pet_ids: set[int] = set()
search_cache: dict[str, list] = {}  # keyed by a strified filter criteria
adoption_status_cache: dict[int, dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helpers


def _filter_key(data: dict) -> str:
    # Create a key from filter criteria dict for caching
    return str(sorted(data.items()))


async def fetch_pets_from_petstore(filters: dict) -> List[dict]:
    """
    Fetch pets from Petstore API applying filters locally after fetching all pets by status if possible.
    Petstore API supports /pet/findByStatus, but no combined filters; we'll filter locally for prototype.
    """
    status = filters.get("status", "available")  # default to 'available' pets
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []

    # Apply additional filters locally: type and name
    filtered = []
    pet_type = filters.get("type")
    name_filter = filters.get("name", "").lower()

    for pet in pets:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            continue
        if name_filter and name_filter not in pet.get("name", "").lower():
            continue
        filtered.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", ""),
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", []) if tag.get("name")] if pet.get("tags") else [],
                "photoUrls": pet.get("photoUrls", []),
            }
        )
    return filtered


async def calculate_adoption_status(pet_ids: List[int]) -> List[dict]:
    """
    Placeholder logic for adoption readiness.
    For prototype: pets with even ID are ready, odds not ready.
    TODO: Replace with real adoption logic or external calls if needed.
    """
    statuses = []
    for pid in pet_ids:
        ready = (pid % 2 == 0)
        statuses.append(
            {
                "petId": pid,
                "readyForAdoption": ready,
                "notes": "Ready for adoption" if ready else "Needs more care",
            }
        )
    return statuses


# Routes


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    key = _filter_key(data)

    if key in search_cache:
        logger.info("Returning cached search result")
        return jsonify({"pets": search_cache[key]})

    # Fire and forget processing task to fetch and cache pets
    async def process_search():
        pets = await fetch_pets_from_petstore(data)
        search_cache[key] = pets

    asyncio.create_task(process_search())

    return jsonify({"message": "Search initiated, results will be cached shortly"}), 202


@app.route("/pets/favorite", methods=["POST"])
async def pets_favorite():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400

    favorite_pet_ids.add(pet_id)
    return jsonify({"message": "Pet added to favorites", "favoritePetIds": list(favorite_pet_ids)})


@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    if not favorite_pet_ids:
        return jsonify({"pets": []})

    # Fetch pets details from Petstore for favorite IDs
    pets = []

    async with httpx.AsyncClient() as client:
        for pid in favorite_pet_ids:
            try:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pid}", timeout=10)
                resp.raise_for_status()
                pet = resp.json()
                pets.append(
                    {
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name", ""),
                        "status": pet.get("status"),
                        "tags": [tag.get("name") for tag in pet.get("tags", []) if tag.get("name")] if pet.get("tags") else [],
                        "photoUrls": pet.get("photoUrls", []),
                    }
                )
            except Exception as e:
                logger.exception(e)
                # Skip pet if error occurs

    return jsonify({"pets": pets})


@app.route("/pets/adoption-status", methods=["POST"])
async def pets_adoption_status():
    data = await request.get_json(force=True)
    pet_ids = data.get("petIds")
    if not isinstance(pet_ids, list) or not all(isinstance(pid, int) for pid in pet_ids):
        return jsonify({"error": "petIds must be a list of integers"}), 400

    # Fire and forget caching adoption statuses
    async def process_adoption():
        statuses = await calculate_adoption_status(pet_ids)
        for s in statuses:
            adoption_status_cache[s["petId"]] = s

    asyncio.create_task(process_adoption())

    # Return immediate 202 to acknowledge processing
    return jsonify({"message": "Adoption status calculation started"}), 202


if __name__ == "__main__":
    import sys

    # Setup logging to console
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
