from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: str = None
    status: str = None

@dataclass
class PetAdopt:
    petId: int

# In-memory caches for quick access
adopted_pets_cache: Dict[str, dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# --- Workflow functions ---

async def process_pet(entity: dict) -> dict:
    # Add timestamp if missing
    if 'created_at' not in entity:
        entity['created_at'] = datetime.utcnow().isoformat() + "Z"

    # Normalize 'type' field to lowercase
    if 'type' in entity and isinstance(entity['type'], str):
        entity['type'] = entity['type'].lower()

    # Example async enrichment: fetch supplementary data about pet's category from entity_service
    category_name = entity.get('category', {}).get('name')
    if category_name:
        try:
            category_details = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="category",
                entity_version=ENTITY_VERSION,
                technical_id=category_name.lower()
            )
            entity['category_details'] = category_details or {}
        except Exception as e:
            logger.warning(f"Failed to fetch category details for '{category_name}': {e}")

    # Fire-and-forget: add a related pet_log entity asynchronously
    async def add_pet_log():
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet_log",
                entity_version=ENTITY_VERSION,
                entity={
                    "pet_id": entity.get("id"),
                    "action": "created",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to add pet_log entity: {e}")

    asyncio.create_task(add_pet_log())

    logger.info(f"Processed pet entity before persistence: {entity}")
    return entity

async def process_pet_search(entity: dict) -> dict:
    pet_type = entity.get('type')
    status = entity.get('status')
    search_id = entity.get('search_id') or str(uuid.uuid4())
    entity['search_id'] = search_id
    entity['results'] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {}
            if status:
                params["status"] = status
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets = resp.json()

        if pet_type:
            pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]

        entity['results'] = pets
        logger.info(f"pet_search {search_id} found {len(pets)} pets")
    except Exception as e:
        logger.warning(f"pet_search {search_id} fetch failed: {e}")
        entity['results'] = []

    return entity

async def process_pet_adopt(entity: dict) -> dict:
    pet_id = str(entity.get('petId') or entity.get('pet_id'))
    if not pet_id:
        logger.warning("pet_adopt entity missing petId")
        return entity

    if pet_id in adopted_pets_cache:
        entity['adopted'] = True
        entity['message'] = "Pet already adopted"
        logger.info(f"Pet {pet_id} already adopted")
        return entity

    mock_pet = {
        "id": pet_id,
        "name": f"Adopted Pet #{pet_id}",
        "type": "unknown",
        "photoUrls": []
    }
    adopted_pets_cache[pet_id] = mock_pet

    entity['adopted'] = True
    entity['message'] = "Pet successfully adopted!"
    logger.info(f"Pet {pet_id} adopted successfully")

    async def add_adoption_log():
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet_adoption_log",
                entity_version=ENTITY_VERSION,
                entity={
                    "pet_id": pet_id,
                    "action": "adopted",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to add pet_adoption_log entity: {e}")

    asyncio.create_task(add_adoption_log())

    return entity

async def process_pet_of_the_day(entity: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()

        for pet in pets:
            if pet.get("photoUrls"):
                entity.clear()
                entity.update({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name", "unknown"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls"),
                    "funFact": f"{pet.get('name', 'This pet')} loves sunny naps! 😸",
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                })
                logger.info(f"Selected pet of the day: {pet.get('name')}")
                break
    except Exception as e:
        logger.warning(f"Failed to select pet of the day: {e}")

    return entity

# --- Endpoints ---

@app.route("/pets", methods=["POST"])
async def create_pet():
    data = await request.get_json()
    pet_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet",
        entity_version=ENTITY_VERSION,
        entity=data,
        workflow=process_pet
    )
    return jsonify({"id": pet_id}), 202

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to get pet"}), 500

@app.route("/pets", methods=["GET"])
async def list_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to list pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["PUT"])
async def update_pet(pet_id: str):
    try:
        data = await request.get_json()
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet updated"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["DELETE"])
async def delete_pet(pet_id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete pet"}), 500

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json()
    entity = {
        "type": data.get("type"),
        "status": data.get("status"),
        "search_id": str(uuid.uuid4())
    }
    search_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_search",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_pet_search
    )
    return jsonify({"searchId": search_id, "count": 0}), 202

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id: str):
    entity = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="pet_search",
        entity_version=ENTITY_VERSION,
        technical_id=search_id
    )
    if entity is None:
        return jsonify({"error": "Search ID not found"}), 404
    pets = entity.get("results", [])
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
async def adopt_pet():
    data = await request.get_json()
    entity = {
        "petId": data.get("petId")
    }
    adopt_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_adopt",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_pet_adopt
    )
    return jsonify({"adoptId": adopt_id}), 202

@app.route("/pets/adopted", methods=["GET"])
async def get_adopted_pets():
    return jsonify({"adoptedPets": list(adopted_pets_cache.values())})

@app.route("/pets/pet-of-the-day", methods=["POST"])
async def update_pet_of_the_day():
    entity = {}
    pet_of_the_day_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_of_the_day",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_pet_of_the_day
    )
    return jsonify({"id": pet_of_the_day_id}), 202

@app.route("/pets/pet-of-the-day", methods=["GET"])
async def get_pet_of_the_day():
    pet_of_the_day = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model="pet_of_the_day",
        entity_version=ENTITY_VERSION
    )
    if not pet_of_the_day:
        return jsonify({"error": "Pet of the day not available"}), 503
    return jsonify(pet_of_the_day[0])

@app.before_serving
async def startup():
    # Initialize pet_of_the_day entity on startup
    try:
        entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet_of_the_day",
            entity_version=ENTITY_VERSION
        )
        if not entities:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet_of_the_day",
                entity_version=ENTITY_VERSION,
                entity={},
                workflow=process_pet_of_the_day
            )
    except Exception as e:
        logger.warning(f"Failed during startup pet_of_the_day init: {e}")

@app.after_serving
async def shutdown():
    pass  # No persistent HTTP client in this refactor; handled per request

if __name__ == '__main__':
    import logging.config
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)