```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for pet details and adoption status
# Structure: pet_id -> pet_data dict
pet_cache: Dict[int, Dict[str, Any]] = {}
# Structure: pet_id -> adoption status (True/False)
adoption_status: Dict[int, bool] = {}

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = 'https://petstore.swagger.io/v2'


async def fetch_pets_from_petstore(search_criteria: Dict[str, Any]) -> list:
    """
    Fetch pets from Petstore API based on search criteria.
    The Petstore API doesn't have a direct search endpoint,
    we'll fetch pets by status and filter locally.
    """
    async with httpx.AsyncClient() as client:
        # Petstore has GET /pet/findByStatus?status=available,pending,sold
        # We will fetch by status if provided, else default to 'available'
        status = search_criteria.get("status", "available")
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []

    # Filter by type and name if provided
    pet_type = search_criteria.get("type")
    name_filter = search_criteria.get("name", "").lower()

    filtered = []
    for pet in pets:
        # Petstore pet category may be None or dict with 'name'
        category_name = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
        # Check type filter
        if pet_type and pet_type.lower() != category_name:
            continue
        # Check name filter (partial match)
        pet_name = pet.get("name", "").lower()
        if name_filter and name_filter not in pet_name:
            continue
        filtered.append(pet)

        # Cache pet for quick GET later (overwrite previous)
        pet_cache[pet["id"]] = pet

    return filtered


async def check_pet_availability(pet_id: int) -> bool:
    """
    Check if pet is available via Petstore API.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pet {pet_id} from Petstore API: {e}")
            return False

    status = pet.get("status")
    return status == "available"


async def process_adoption(pet_id: int, adopter_name: str, contact: str) -> Dict[str, Any]:
    """
    Process pet adoption request:
    - Check availability
    - Mark locally as adopted (mock persistence)
    """
    available = await check_pet_availability(pet_id)
    if not available:
        return {"success": False, "message": f"Pet id {pet_id} is not available for adoption."}

    # TODO: In real app, update database and Petstore API accordingly.
    # Here we only mark locally.
    adoption_status[pet_id] = True

    pet = pet_cache.get(pet_id)
    pet_name = pet.get("name") if pet else f"#{pet_id}"

    return {"success": True, "message": f"Pet {pet_name} adopted successfully!"}


async def get_fun_pet_fact(pet_type: str = None) -> str:
    """
    Return a fun pet fact or joke optionally filtered by pet type.
    We'll use a small predefined set for demo.
    """
    facts = {
        "cat": [
            "Cats sleep for 70% of their lives.",
            "A group of cats is called a clowder."
        ],
        "dog": [
            "Dogs can learn more than 1000 words!",
            "Dogs have three eyelids."
        ],
        "default": [
            "Pets bring joy to our lives!",
            "Animals have a sense of time and can miss you."
        ]
    }

    pet_type_lower = (pet_type or "").lower()
    selected_facts = facts.get(pet_type_lower, facts["default"])

    # Pick a random fact
    import random
    return random.choice(selected_facts)


@app.route('/pets/search', methods=['POST'])
async def pets_search():
    data = await request.get_json(force=True)
    pets = await fetch_pets_from_petstore(data or {})
    # Format response as per spec:
    results = []
    for pet in pets:
        results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
            "description": pet.get("description", "") or ""
        })
    return jsonify({"results": results})


@app.route('/pets/adopt', methods=['POST'])
async def pets_adopt():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    adopter_name = data.get("adopterName")
    contact = data.get("contact")

    if not all([pet_id, adopter_name, contact]):
        return jsonify({"success": False, "message": "petId, adopterName and contact are required."}), 400

    result = await process_adoption(pet_id, adopter_name, contact)
    return jsonify(result)


@app.route('/pets/fun-facts', methods=['POST'])
async def pets_fun_facts():
    data = await request.get_json(force=True)
    pet_type = data.get("type") if data else None
    fact = await get_fun_pet_fact(pet_type)
    return jsonify({"fact": fact})


@app.route('/pets/<int:pet_id>', methods=['GET'])
async def pets_get(pet_id: int):
    pet = pet_cache.get(pet_id)
    if not pet:
        # Try fetch directly from Petstore API on demand
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                resp.raise_for_status()
                pet = resp.json()
                pet_cache[pet_id] = pet  # Cache for future
            except Exception as e:
                logger.exception(f"Failed to fetch pet {pet_id} from Petstore API: {e}")
                return jsonify({"message": "Pet not found"}), 404

    response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "description": pet.get("description", "") or ""
    }
    return jsonify(response)


if __name__ == '__main__':
    import sys

    # Setup basic logging to stdout
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s',
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```