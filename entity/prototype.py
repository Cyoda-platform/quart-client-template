from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: str = None
    status: str = None

@dataclass
class PetAdopt:
    petId: int

# In-memory "database" caches (async-safe by design of Quart single-threaded nature)
pets_search_cache: Dict[str, List[dict]] = {}
adopted_pets_cache: Dict[int, dict] = {}
pet_of_the_day_cache: dict = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
async_client = httpx.AsyncClient(timeout=10.0)

async def fetch_pets_from_petstore(pet_type: str = None, status: str = None) -> List[dict]:
    params = {}
    if status:
        params["status"] = status
    try:
        response = await async_client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
        response.raise_for_status()
        pets = response.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        return []
    if pet_type:
        pets = [pet for pet in pets if pet.get("category") and pet["category"].get("name", "").lower() == pet_type.lower()]
    return pets

async def process_search(search_id: str, pet_type: str = None, status: str = None):
    try:
        pets = await fetch_pets_from_petstore(pet_type, status)
        pets_search_cache[search_id] = pets
        logger.info(f"Search {search_id} completed with {len(pets)} pets")
    except Exception as e:
        logger.exception(f"Error processing search {search_id}")
        pets_search_cache[search_id] = []

async def select_pet_of_the_day():
    try:
        pets = await fetch_pets_from_petstore(status="available")
        if not pets:
            return
        for pet in pets:
            if pet.get("photoUrls"):
                pet_of_the_day_cache.clear()
                pet_of_the_day_cache.update({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name", "Unknown"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls"),
                    "funFact": f"{pet.get('name', 'This pet')} loves sunny naps! 😸"  # TODO: replace with real fun facts
                })
                logger.info(f"Selected pet of the day: {pet.get('name')}")
                break
    except Exception as e:
        logger.exception("Failed to select pet of the day")

@app.route("/pets/search", methods=["POST"])
# workaround for validate_request defect: validation last for POST
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    pet_type = data.type
    status = data.status
    search_id = str(uuid.uuid4())
    pets_search_cache[search_id] = []
    requested_at = datetime.utcnow()
    asyncio.create_task(process_search(search_id, pet_type, status))
    return jsonify({"searchId": search_id, "count": 0}), 202

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    pets = pets_search_cache.get(search_id)
    if pets is None:
        return jsonify({"error": "Search ID not found"}), 404
    def normalize_pet(pet):
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls") or [],
        }
    normalized = [normalize_pet(p) for p in pets]
    return jsonify({"searchId": search_id, "pets": normalized})

@app.route("/pets/adopt", methods=["POST"])
# workaround for validate_request defect: validation last for POST
@validate_request(PetAdopt)
async def adopt_pet(data: PetAdopt):
    pet_id = data.petId
    if pet_id in adopted_pets_cache:
        return jsonify({"petId": pet_id, "adopted": True, "message": "Pet already adopted"}), 200
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
    return jsonify({"adoptedPets": list(adopted_pets_cache.values())})

@app.route("/pets/pet-of-the-day", methods=["GET"])
async def get_pet_of_the_day():
    if not pet_of_the_day_cache:
        await select_pet_of_the_day()
    if not pet_of_the_day_cache:
        return jsonify({"error": "Pet of the day not available"}), 503
    return jsonify(pet_of_the_day_cache)

@app.before_serving
async def startup():
    await select_pet_of_the_day()

@app.after_serving
async def shutdown():
    await async_client.aclose()

if __name__ == '__main__':
    import logging.config
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)