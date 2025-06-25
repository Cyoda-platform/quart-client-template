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

# Local in-memory cache for pets data and adoption status
# Structure:
# pets_cache: Dict[int, dict] - keyed by pet ID
# adopt_status: Dict[int, str] - pet ID -> status ("available", "adopted", etc)
pets_cache: Dict[int, dict] = {}
adopt_status: Dict[int, str] = {}

# Using Petstore Swagger sample API:
# GET https://petstore3.swagger.io/api/v3/pet/findByStatus?status=available
# GET https://petstore3.swagger.io/api/v3/pet/{petId}
# POST https://petstore3.swagger.io/api/v3/pet (for updating pet)
PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"


async def fetch_pets_from_petstore(
    type_filter: Optional[str] = None, status_filter: Optional[str] = None
) -> List[dict]:
    """
    Fetch pets from external Petstore API filtered by status.
    Petstore API does not support filtering by type directly,
    so filtering by type is done locally after fetching by status.
    """
    status = status_filter or "available"
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore API: {e}")
            return []

    # Petstore API returns list of pets (or empty list)
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets


async def update_pet_adoption_status_in_petstore(pet_id: int) -> bool:
    """
    Mark pet as adopted by updating its status in Petstore.

    Petstore API expects full pet object for update (PUT /pet),
    so we must get pet details, modify status, then PUT back.

    TODO: This is a simplified approach; Petstore API is a demo and may not persist changes.
    """
    get_url = f"{PETSTORE_BASE}/pet/{pet_id}"
    update_url = f"{PETSTORE_BASE}/pet"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(get_url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if not pet:
                logger.info(f"Pet ID {pet_id} not found in Petstore.")
                return False

            pet["status"] = "adopted"

            resp_update = await client.put(update_url, json=pet, timeout=10)
            resp_update.raise_for_status()

            return True
        except Exception as e:
            logger.exception(f"Failed to update adoption status in Petstore for pet {pet_id}: {e}")
            return False


async def process_fetch_pets(data: dict):
    """
    Background task: fetch pets from external API, update local cache.
    """
    pets = await fetch_pets_from_petstore(
        type_filter=data.get("type"),
        status_filter=data.get("status"),
    )
    for pet in pets:
        pet_id = pet.get("id")
        if not pet_id:
            continue
        pets_cache[pet_id] = pet
        # sync local adopt status from pet.status if present, else "available"
        adopt_status[pet_id] = pet.get("status", "available")


async def process_adopt_pet(pet_id: int) -> bool:
    """
    Background task: update adoption status remotely and locally.
    """
    success = await update_pet_adoption_status_in_petstore(pet_id)
    if success:
        adopt_status[pet_id] = "adopted"
        # Update local pet cache status if exists
        if pet_id in pets_cache:
            pets_cache[pet_id]["status"] = "adopted"
    return success


@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    data = await request.get_json(force=True)
    # Fire and forget background processing
    asyncio.create_task(process_fetch_pets(data))

    return jsonify({"message": "Pet data fetch started. Please GET /pets to see cached results."}), 202


@app.route("/pets/adopt", methods=["POST"])
async def adopt_pet():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not pet_id or not isinstance(pet_id, int):
        return jsonify({"error": "petId must be provided as an integer"}), 400

    # Check if pet exists locally
    if pet_id not in pets_cache:
        return jsonify({"error": f"Pet with ID {pet_id} not found in local cache. Please fetch pets first."}), 404

    # Process adoption in background and wait for result here (to confirm adoption)
    success = await process_adopt_pet(pet_id)
    if not success:
        return jsonify({"error": "Failed to adopt pet via external API."}), 500

    return jsonify({"message": f"Pet with ID {pet_id} has been adopted."})


@app.route("/pets", methods=["GET"])
async def get_pets():
    # Return locally cached pets with their current adoption status
    pets_list = []
    for pet_id, pet in pets_cache.items():
        pet_copy = pet.copy()
        pet_copy["status"] = adopt_status.get(pet_id, pet_copy.get("status", "unknown"))
        pets_list.append(pet_copy)
    return jsonify({"pets": pets_list})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": f"Pet with ID {pet_id} not found in local cache."}), 404
    pet_copy = pet.copy()
    pet_copy["status"] = adopt_status.get(pet_id, pet_copy.get("status", "unknown"))
    return jsonify(pet_copy)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
