```python
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" caches (async-safe by design of Quart single-threaded nature)
# We store search results, adopted pets, and pet-of-the-day selection here.
pets_search_cache: Dict[str, List[dict]] = {}
adopted_pets_cache: Dict[int, dict] = {}
pet_of_the_day_cache: dict = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# HTTP client for external Petstore API
async_client = httpx.AsyncClient(timeout=10.0)


async def fetch_pets_from_petstore(pet_type: str = None, status: str = None) -> List[dict]:
    """
    Fetch pets from Petstore API filtered by type and status.
    Petstore API has /pet/findByStatus endpoint to filter by status.
    Type filtering will be done client-side since Petstore API does not support type filtering.
    """
    params = {}
    # Petstore only supports filtering by status (comma separated)
    if status:
        params["status"] = status

    try:
        response = await async_client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
        response.raise_for_status()
        pets = response.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        return []

    # Filter by type client-side if specified
    if pet_type:
        pets = [pet for pet in pets if pet.get("category") and pet["category"].get("name", "").lower() == pet_type.lower()]

    return pets


async def process_search(search_id: str, pet_type: str = None, status: str = None):
    """
    Fetch pets and store them by search_id.
    """
    try:
        pets = await fetch_pets_from_petstore(pet_type, status)
        pets_search_cache[search_id] = pets
        logger.info(f"Search {search_id} completed with {len(pets)} pets")
    except Exception as e:
        logger.exception(f"Error processing search {search_id}")
        pets_search_cache[search_id] = []


async def select_pet_of_the_day():
    """
    Select a pet of the day from Petstore available pets.
    This runs once at startup and can be refreshed later if needed.
    """
    try:
        pets = await fetch_pets_from_petstore(status="available")
        if not pets:
            return

        # Simple selection: pick the first pet that has photos
        for pet in pets:
            if pet.get("photoUrls"):
                # Add a fun fact placeholder
                pet_of_the_day_cache.clear()
                pet_of_the_day_cache.update({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name", "Unknown"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls"),
                    "funFact": f"{pet.get('name', 'This pet')} loves sunny naps! 😸"  # TODO: Replace with real fun facts source
                })
                logger.info(f"Selected pet of the day: {pet.get('name')}")
                break
    except Exception as e:
        logger.exception("Failed to select pet of the day")


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")

    search_id = str(uuid.uuid4())
    pets_search_cache[search_id] = []  # Mark as processing (empty list)
    requested_at = datetime.utcnow()

    # Fire and forget processing
    asyncio.create_task(process_search(search_id, pet_type, status))

    return jsonify({"searchId": search_id, "count": 0}), 202


@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    pets = pets_search_cache.get(search_id)
    if pets is None:
        return jsonify({"error": "Search ID not found"}), 404

    # Return all pets found
    # Normalize pet data as per spec
    def normalize_pet(pet):
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls") or [],
        }

    normalized_pets = [normalize_pet(p) for p in pets]

    return jsonify({"searchId": search_id, "pets": normalized_pets})


@app.route("/pets/adopt", methods=["POST"])
async def adopt_pet():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")

    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400

    # Check if already adopted
    if pet_id in adopted_pets_cache:
        return jsonify({"petId": pet_id, "adopted": True, "message": "Pet already adopted"}), 200

    # TODO: Ideally verify pet exists - for prototype we skip this or search in cached data
    # For now, mock minimal pet info for adopted pet
    mock_pet = {
        "id": pet_id,
        "name": f"Adopted Pet #{pet_id}",
        "type": "Unknown",
        "photoUrls": []
    }

    adopted_pets_cache[pet_id] = mock_pet
    logger.info(f"Pet {pet_id} adopted")

    return jsonify({"petId": pet_id, "adopted": True, "message": "Pet successfully adopted!"})


@app.route("/pets/adopted", methods=["GET"])
async def get_adopted_pets():
    adopted_list = list(adopted_pets_cache.values())
    return jsonify({"adoptedPets": adopted_list})


@app.route("/pets/pet-of-the-day", methods=["GET"])
async def get_pet_of_the_day():
    if not pet_of_the_day_cache:
        await select_pet_of_the_day()
    if not pet_of_the_day_cache:
        return jsonify({"error": "Pet of the day not available"}), 503

    return jsonify(pet_of_the_day_cache)


@app.before_serving
async def startup():
    # Initialize pet of the day at startup
    await select_pet_of_the_day()


@app.after_serving
async def shutdown():
    # Cleanup httpx client properly
    await async_client.aclose()


if __name__ == '__main__':
    import logging.config
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
