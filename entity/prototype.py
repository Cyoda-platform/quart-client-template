import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SearchRequest:
    type: Optional[str] = None
    status: Optional[str] = None
    nameContains: Optional[str] = None

@dataclass
class FavoriteRequest:
    petId: int
    userId: str

_search_results_cache: Dict[str, Dict] = {}
_user_favorites_cache: Dict[str, set] = {}

FUN_FACTS = {
    "cat": "Cats are curious and love to explore!",
    "dog": "Dogs are loyal and friendly companions.",
    "bird": "Birds are social and enjoy singing.",
    "rabbit": "Rabbits have nearly 360-degree panoramic vision.",
}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
http_client = httpx.AsyncClient(timeout=10.0)

async def fetch_pets_from_petstore(
    type_filter: Optional[str], status_filter: Optional[str], name_contains: Optional[str]
) -> List[Dict]:
    pets = []
    try:
        status_query = status_filter if status_filter else "available"
        url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
        response = await http_client.get(url, params={"status": status_query})
        response.raise_for_status()
        pet_list = response.json()
        for pet in pet_list:
            pet_type = None
            if pet.get("category") and isinstance(pet["category"], dict):
                pet_type = pet["category"].get("name", "").lower()
            if type_filter and (not pet_type or pet_type != type_filter.lower()):
                continue
            pet_name = pet.get("name", "").lower()
            if name_contains and name_contains.lower() not in pet_name:
                continue
            pets.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet_type or "unknown",
                "status": status_query,
            })
    except Exception as e:
        logger.exception(f"Error fetching pets from Petstore API: {e}")
    return pets

async def process_search_request(search_id: str, criteria: dict):
    try:
        pets = await fetch_pets_from_petstore(
            criteria.get("type"),
            criteria.get("status"),
            criteria.get("nameContains"),
        )
        for pet in pets:
            fact = FUN_FACTS.get(pet["type"].lower(), "Every pet is unique and special!")
            pet["funFact"] = fact
        _search_results_cache[search_id] = {
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "criteria": criteria,
            "pets": pets,
            "status": "completed",
        }
        logger.info(f"Search completed for searchId={search_id}, {len(pets)} pets found")
    except Exception as e:
        logger.exception(f"Failed processing search {search_id}: {e}")
        _search_results_cache[search_id] = {
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "criteria": criteria,
            "pets": [],
            "status": "failed",
        }

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)  # Workaround: validate_request last for POST due to quart-schema issue
async def pets_search(data: SearchRequest):
    search_id = str(uuid.uuid4())
    _search_results_cache[search_id] = {
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "criteria": data.__dict__,
        "pets": [],
        "status": "processing",
    }
    asyncio.create_task(process_search_request(search_id, data.__dict__))
    return jsonify({"searchId": search_id})

@app.route("/pets/results/<string:search_id>", methods=["GET"])
async def pets_results(search_id):
    result = _search_results_cache.get(search_id)
    if not result:
        return jsonify({"error": "searchId not found"}), 404
    return jsonify({
        "searchId": search_id,
        "status": result.get("status", "unknown"),
        "pets": result.get("pets", []),
    })

@app.route("/pets/favorite", methods=["POST"])
@validate_request(FavoriteRequest)  # Workaround: validate_request last for POST due to quart-schema issue
async def pets_favorite(data: FavoriteRequest):
    pet_id = data.petId
    user_id = data.userId
    if pet_id is None or not user_id:
        return jsonify({"error": "petId and userId required"}), 400
    favorites = _user_favorites_cache.setdefault(user_id, set())
    favorites.add(pet_id)
    return jsonify({"success": True})

@app.route("/pets/favorites/<string:user_id>", methods=["GET"])
async def pets_favorites(user_id):
    favorites = _user_favorites_cache.get(user_id, set())
    pets_result = []
    all_pets = []
    for search_data in _search_results_cache.values():
        if search_data.get("status") != "completed":
            continue
        all_pets.extend(search_data.get("pets", []))
    pet_map = {pet["id"]: pet for pet in all_pets}
    for pet_id in favorites:
        pet = pet_map.get(pet_id)
        if pet:
            pets_result.append({
                "id": pet["id"],
                "name": pet["name"],
                "type": pet["type"],
                "status": pet["status"],
            })
        else:
            pets_result.append({
                "id": pet_id,
                "name": "Unknown",
                "type": "Unknown",
                "status": "Unknown",
            })
    return jsonify({"userId": user_id, "favorites": pets_result})

@app.before_serving
async def startup():
    logger.info("Purrfect Pets API starting up...")

@app.after_serving
async def shutdown():
    await http_client.aclose()
    logger.info("Purrfect Pets API shutting down...")

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)