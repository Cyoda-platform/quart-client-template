from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache simulating persistence
user_data_cache: Dict[str, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

@dataclass
class SearchRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class PetIdRequest:
    petId: int

async def fetch_pets_from_petstore(pet_type: str = None, status: str = None) -> List[Dict[str, Any]]:
    params = {}
    if status:
        params["status"] = status
    else:
        params["status"] = "available"
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []
    if pet_type:
        return [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    return pets

def pet_to_response_obj(pet: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", ""),
        "status": pet.get("status", ""),
        "photoUrls": pet.get("photoUrls", []),
    }

def get_user_favorites(user_id: str) -> set:
    return user_data_cache.get(user_id, {}).get("favorites", set())

def add_user_favorite(user_id: str, pet_id: int):
    if user_id not in user_data_cache:
        user_data_cache[user_id] = {"favorites": set()}
    user_data_cache[user_id]["favorites"].add(pet_id)

def remove_user_favorite(user_id: str, pet_id: int):
    if user_id in user_data_cache:
        user_data_cache[user_id]["favorites"].discard(pet_id)

async def fetch_pets_by_ids(pet_ids: set) -> List[Dict[str, Any]]:
    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        for pet_id in pet_ids:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                if r.status_code == 200:
                    pets.append(r.json())
            except Exception as e:
                logger.exception(f"Error fetching pet id {pet_id}: {e}")
    return pets

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)  # Workaround for quart-schema decorator order defect: POST validator last
async def pets_search(data: SearchRequest):
    pets = await fetch_pets_from_petstore(data.type, data.status)
    return jsonify({"pets": [pet_to_response_obj(p) for p in pets]})

@app.route("/favorites/add", methods=["POST"])
@validate_request(PetIdRequest)  # Workaround for quart-schema decorator order defect: POST validator last
async def favorites_add(data: PetIdRequest):
    user_id = "dummy_user"  # TODO: replace with real auth
    add_user_favorite(user_id, data.petId)
    count = len(get_user_favorites(user_id))
    return jsonify({"message": "Pet added to favorites", "favoriteCount": count})

@app.route("/favorites/remove", methods=["POST"])
@validate_request(PetIdRequest)  # Workaround for quart-schema decorator order defect: POST validator last
async def favorites_remove(data: PetIdRequest):
    user_id = "dummy_user"
    remove_user_favorite(user_id, data.petId)
    count = len(get_user_favorites(user_id))
    return jsonify({"message": "Pet removed from favorites", "favoriteCount": count})

@app.route("/favorites", methods=["GET"])
async def favorites_get():
    user_id = "dummy_user"
    pet_ids = get_user_favorites(user_id)
    pets = await fetch_pets_by_ids(pet_ids)
    return jsonify({"favorites": [pet_to_response_obj(p) for p in pets]})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)