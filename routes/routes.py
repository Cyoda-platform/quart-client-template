from dataclasses import dataclass
from typing import List, Optional
import asyncio
import logging
import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

ENTITY_NAME = "pet"  # entity name in underscore lowercase

@dataclass
class SearchPetsRequest:
    type: str
    status: Optional[str]
    name: Optional[str]

@dataclass
class AddPetRequest:
    name: str
    type: str
    status: str
    photoUrls: List[str]

@dataclass
class UpdatePetRequest:
    name: Optional[str]
    status: Optional[str]
    photoUrls: Optional[List[str]]

pets_cache = {}
pets_cache_lock = asyncio.Lock()

async def fetch_petstore_pets(filters: dict):
    status = filters.get("status")
    if status not in ("available", "pending", "sold"):
        status = "available"
    url = f"https://petstore.swagger.io/v2/pet/findByStatus?status={status}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception:
            logger.exception("Error fetching pets from Petstore API")
            return []
    type_filter = filters.get("type", "all").lower()
    name_filter = (filters.get("name") or "").lower()
    def pet_matches(pet):
        pet_type = (pet.get("category") or {}).get("name", "").lower()
        if type_filter != "all" and pet_type != type_filter:
            return False
        if name_filter and name_filter not in (pet.get("name") or "").lower():
            return False
        return True
    filtered = [p for p in pets if pet_matches(p)]
    normalized = []
    for p in filtered:
        normalized.append({
            "id": str(p.get("id")),
            "name": p.get("name"),
            "type": (p.get("category") or {}).get("name", "unknown"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        })
    return normalized

async def process_pet(entity: dict) -> dict:
    # Normalize status to lowercase
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    # Normalize category name to lowercase
    if "category" in entity and isinstance(entity["category"], dict):
        name = entity["category"].get("name")
        if name and isinstance(name, str):
            entity["category"]["name"] = name.lower()
    # Add created_at timestamp if not present
    if "created_at" not in entity:
        entity["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    # Placeholder for additional enrichment or async calls
    return entity

async def process_pet_update(entity: dict) -> dict:
    # Normalize status to lowercase if present
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    if "category" in entity and isinstance(entity["category"], dict):
        name = entity["category"].get("name")
        if name and isinstance(name, str):
            entity["category"]["name"] = name.lower()
    # Add updated_at timestamp
    entity["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPetsRequest)
async def pets_search(data: SearchPetsRequest):
    filters = {"type": data.type, "status": data.status, "name": data.name}
    pets = await fetch_petstore_pets(filters)
    async with pets_cache_lock:
        for pet in pets:
            pets_cache[pet["id"]] = pet
    return jsonify({"pets": pets})

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)
async def pets_add(data: AddPetRequest):
    if data.type not in ("cat", "dog") or data.status not in ("available", "pending", "sold"):
        return jsonify({"message": "Invalid input"}), 400
    petstore_pet = {
        "name": data.name,
        "category": {"id": 0, "name": data.type},
        "photoUrls": data.photoUrls,
        "status": data.status,
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=petstore_pet
        )
    except Exception:
        logger.exception("Error adding pet via entity_service")
        return jsonify({"message": "Failed to add pet"}), 500
    async with pets_cache_lock:
        pets_cache[str(pet_id)] = {**petstore_pet, "id": str(pet_id)}
    return jsonify({"message": "Pet added successfully", "petId": str(pet_id)})

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pets_get(pet_id: str):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
        try:
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
        except Exception:
            logger.exception("Error fetching pet detail from entity_service")
            return jsonify({"message": "Error fetching pet data"}), 500
        if not pet:
            return jsonify({"message": "Pet not found"}), 404
        pet["type"] = (pet.get("category") or {}).get("name", "unknown")
        async with pets_cache_lock:
            pets_cache[pet_id] = pet
    return jsonify(pet)

@app.route("/pets/update/<string:pet_id>", methods=["POST"])
@validate_request(UpdatePetRequest)
async def pets_update(data: UpdatePetRequest, pet_id: str):
    async with pets_cache_lock:
        pet = pets_cache.get(pet_id)
    if not pet:
        try:
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
        except Exception:
            logger.exception("Error fetching pet for update")
            return jsonify({"message": "Error fetching pet data"}), 500
        if not pet:
            return jsonify({"message": "Pet not found"}), 404
    updated_pet = {
        "id": pet_id,
        "name": data.name if data.name is not None else pet.get("name"),
        "category": {"id": 0, "name": pet.get("type") or (pet.get("category") or {}).get("name", "unknown")},
        "status": data.status if data.status is not None else pet.get("status"),
        "photoUrls": data.photoUrls if data.photoUrls is not None else pet.get("photoUrls", []),
    }
    try:
        updated_pet = await process_pet_update(updated_pet)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=updated_pet,
            technical_id=pet_id,
            meta={}
        )
    except Exception:
        logger.exception("Failed to update pet via entity_service")
        return jsonify({"message": "Failed to update pet"}), 500
    async with pets_cache_lock:
        pets_cache[pet_id] = {
            "id": pet_id,
            "name": updated_pet["name"],
            "type": updated_pet["category"]["name"],
            "status": updated_pet["status"],
            "photoUrls": updated_pet["photoUrls"],
        }
    return jsonify({"message": "Pet updated successfully"})

@app.route("/pets/delete/<string:pet_id>", methods=["POST"])
async def pets_delete(pet_id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
    except Exception:
        logger.exception("Failed to delete pet via entity_service")
        return jsonify({"message": "Failed to delete pet"}), 500
    async with pets_cache_lock:
        pets_cache.pop(pet_id, None)
    return jsonify({"message": "Pet deleted successfully"})

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
