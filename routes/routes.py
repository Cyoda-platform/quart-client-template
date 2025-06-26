import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory caches with asyncio.Lock for concurrency safety
search_cache = {"data": None, "lock": asyncio.Lock()}
favorites_cache = {"data": set(), "lock": asyncio.Lock()}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

@dataclass
class PetSearchRequest:
    type: Optional[str]
    status: Optional[str]

@dataclass
class PetDetailsRequest:
    id: str

@dataclass
class FavoriteRequest:
    id: str

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]):
    params = {}
    if status:
        params["status"] = status
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except Exception:
            logger.exception("Error fetching pets from Petstore API")
            return []

async def fetch_pet_details_from_petstore(pet_id: str):
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception(f"Error fetching pet details for id {pet_id}")
            return None

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def search_pets(data: PetSearchRequest):
    pets = await fetch_pets_from_petstore(data.type, data.status)
    async with search_cache["lock"]:
        search_cache["data"] = pets
    return jsonify({"pets": pets})

@app.route("/pets", methods=["GET"])
async def get_last_search():
    async with search_cache["lock"]:
        pets = search_cache["data"]
    if pets is None:
        return jsonify({"pets": []})
    return jsonify({"pets": pets})

@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pet_details(data: PetDetailsRequest):
    pet = await fetch_pet_details_from_petstore(data.id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/favorites", methods=["GET"])
async def get_favorites():
    async with favorites_cache["lock"]:
        fav_ids = list(favorites_cache["data"])

    async def fetch_one(pet_id: str):
        pet = await fetch_pet_details_from_petstore(pet_id)
        if pet:
            return {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
            }
        return None

    pets = await asyncio.gather(*(fetch_one(pid) for pid in fav_ids))
    pets = [p for p in pets if p is not None]
    return jsonify({"favorites": pets})

@app.route("/pets/favorites", methods=["POST"])
@validate_request(FavoriteRequest)
async def add_favorite(data: FavoriteRequest):
    pet = await fetch_pet_details_from_petstore(data.id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    async with favorites_cache["lock"]:
        favorites_cache["data"].add(data.id)
    response = {
        "message": "Pet added to favorites",
        "pet": {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
        },
    }
    return jsonify(response)

# Workflow function for pet entity enrichment before persistence
async def process_pet(entity):
    try:
        # Add processing timestamp if missing
        if "processed_at" not in entity:
            entity["processed_at"] = datetime.utcnow().isoformat() + "Z"

        # Enrich description if missing and id is present
        if (not entity.get("description")) and entity.get("id"):
            pet_id = str(entity["id"])
            pet_details = await fetch_pet_details_from_petstore(pet_id)
            if pet_details and pet_details.get("description"):
                entity["description"] = pet_details["description"]
        # Additional async tasks or related entities can be handled here
    except Exception:
        logger.exception("Exception in process_pet workflow")
    return entity  # modifications done in place; return optional

@app.route("/entity/pet", methods=["POST"])
async def add_pet():
    try:
        data = await request.get_json()
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({"id": pet_id})
    except Exception:
        logger.exception("Failed to add pet")
        return jsonify({"error": "Failed to add pet"}), 500

@app.route("/entity/pet/<string:id>", methods=["GET"])
async def get_pet(id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception:
        logger.exception("Failed to get pet")
        return jsonify({"error": "Failed to get pet"}), 500

@app.route("/entity/pet", methods=["GET"])
async def get_all_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception:
        logger.exception("Failed to get pets")
        return jsonify({"error": "Failed to get pets"}), 500

@app.route("/entity/pet/<string:id>", methods=["PUT"])
async def update_pet(id):
    try:
        data = await request.get_json()
        # No workflow on update by default; add if needed in future
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=id,
            meta={}
        )
        return jsonify({"message": "Pet updated"})
    except Exception:
        logger.exception("Failed to update pet")
        return jsonify({"error": "Failed to update pet"}), 500

@app.route("/entity/pet/<string:id>", methods=["DELETE"])
async def delete_pet(id):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=id,
            meta={}
        )
        return jsonify({"message": "Pet deleted"})
    except Exception:
        logger.exception("Failed to delete pet")
        return jsonify({"error": "Failed to delete pet"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)