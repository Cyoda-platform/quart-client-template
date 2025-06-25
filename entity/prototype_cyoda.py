from dataclasses import dataclass
from typing import Optional, List
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

favorites_lock = asyncio.Lock()
favorites_cache: Dict[str, dict] = {}

@dataclass
class PetSearch:
    status: Optional[str]
    type: Optional[str]

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    photoUrls: List[str]

@dataclass
class PetUpdate:
    id: str  # id is now string
    name: Optional[str]
    status: Optional[str]
    photoUrls: Optional[List[str]]
    type: Optional[str]

@dataclass
class PetId:
    id: str  # id is now string

# Remove previous petstore APIs that used httpx, replaced with entity_service calls

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    # Build condition for entity_service.get_items_by_condition
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": []
        }
    }
    if data.status is not None:
        condition["cyoda"]["conditions"].append({
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": data.status,
            "type": "simple"
        })
    if data.type is not None:
        condition["cyoda"]["conditions"].append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": data.type,
            "type": "simple"
        })
    try:
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(f"Error fetching pets: {e}")
        pets = []
    result = []
    for pet in pets:
        result.append({
            "id": pet.get("technical_id") or pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", [])
        })
    return jsonify({"pets": result})

@app.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)
async def pets_add(data: PetAdd):
    pet_payload = {
        "name": data.name,
        "photoUrls": data.photoUrls,
        "status": data.status,
        "category": {"id": 0, "name": data.type},
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_payload
        )
    except Exception as e:
        logger.exception(f"Error adding pet: {e}")
        return jsonify({"success": False}), 500
    return jsonify({"success": True, "petId": str(pet_id)})

@app.route("/pets/update", methods=["POST"])
@validate_request(PetUpdate)
async def pets_update(data: PetUpdate):
    if not data.id:
        return jsonify({"success": False, "error": "Missing pet id"}), 400
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=data.id
        )
    except Exception as e:
        logger.exception(f"Error fetching pet: {e}")
        return jsonify({"success": False, "error": "Pet not found"}), 404
    if data.name is not None:
        pet["name"] = data.name
    if data.status is not None:
        pet["status"] = data.status
    if data.photoUrls is not None:
        pet["photoUrls"] = data.photoUrls
    if data.type is not None:
        pet["category"] = {"id": 0, "name": data.type}
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=data.id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Error updating pet: {e}")
        return jsonify({"success": False}), 500
    return jsonify({"success": True})

@app.route("/pets/delete", methods=["POST"])
@validate_request(PetId)
async def pets_delete(data: PetId):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=data.id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Error deleting pet: {e}")
        return jsonify({"success": False}), 500
    async with favorites_lock:
        favorites_cache.pop(data.id, None)
    return jsonify({"success": True})

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    async with favorites_lock:
        favs = list(favorites_cache.values())
    return jsonify({"favorites": favs})

@app.route("/pets/favorites/add", methods=["POST"])
@validate_request(PetId)
async def pets_favorites_add(data: PetId):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=data.id
        )
    except Exception as e:
        logger.exception(f"Error fetching pet: {e}")
        return jsonify({"success": False, "error": "Pet not found"}), 404
    pet_fav = {"id": data.id, "name": pet.get("name"), "type": pet.get("category", {}).get("name", ""), "status": pet.get("status")}
    async with favorites_lock:
        favorites_cache[data.id] = pet_fav
    return jsonify({"success": True})

@app.route("/pets/favorites/remove", methods=["POST"])
@validate_request(PetId)
async def pets_favorites_remove(data: PetId):
    async with favorites_lock:
        favorites_cache.pop(data.id, None)
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)