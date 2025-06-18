from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

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

# Request schemas
@dataclass
class SearchReq:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class FavoriteReq:
    userId: str
    petId: int

@dataclass
class RecommendReq:
    userId: str
    preferences: Dict[str, Optional[str]]

# In-memory cache for favorites: {userId: set(petId)}
favorites_cache: Dict[str, set] = {}

# In-memory cache for search results keyed by request id
search_cache: Dict[str, List[Dict]] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(
    type_: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            pet_status = status or "available"
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": pet_status})
            r.raise_for_status()
            pets = r.json()

            filtered = []
            for pet in pets:
                if type_:
                    cat = pet.get("category", {}).get("name")
                    if not cat or cat.lower() != type_.lower():
                        continue
                if name and pet.get("name"):
                    if name.lower() not in pet["name"].lower():
                        continue
                filtered.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name", ""),
                    "status": pet_status,
                    "photoUrls": pet.get("photoUrls", [])
                })
            return filtered
    except Exception as e:
        logger.exception(e)
        return []

@app.route("/pets/search", methods=["POST"])
# Issue workaround: validate_request must go last for POST methods
@validate_request(SearchReq)
async def pets_search(data: SearchReq):
    pets = await fetch_pets_from_petstore(data.type, data.status, data.name)
    request_id = datetime.utcnow().isoformat()
    search_cache[request_id] = pets
    return jsonify({"pets": pets})

@app.route("/pets/favorites", methods=["POST"])
# Issue workaround: validate_request must go last for POST methods
@validate_request(FavoriteReq)
async def add_favorite(data: FavoriteReq):
    user_favs = favorites_cache.setdefault(data.userId, set())
    user_favs.add(data.petId)
    return jsonify({"message": "Pet added to favorites"})

@app.route("/pets/favorites/<user_id>", methods=["GET"])
async def get_favorites(user_id: str):
    user_favs = favorites_cache.get(user_id, set())
    if not user_favs:
        return jsonify({"favorites": []})
    pets = []
    async with httpx.AsyncClient() as client:
        for pet_id in user_favs:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                if r.status_code == 200:
                    pet = r.json()
                    pets.append({
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name", ""),
                        "status": pet.get("status", "")
                    })
                else:
                    logger.info(f"Pet id {pet_id} not found")
            except Exception as e:
                logger.exception(e)
    return jsonify({"favorites": pets})

@app.route("/pets/recommend", methods=["POST"])
# Issue workaround: validate_request must go last for POST methods
@validate_request(RecommendReq)
async def recommend_pets(data: RecommendReq):
    prefs = data.preferences or {}
    pets = await fetch_pets_from_petstore(prefs.get("type"), prefs.get("status", "available"), None)
    user_favs = favorites_cache.get(data.userId, set())
    recommended = [pet for pet in pets if pet["id"] not in user_favs][:5]
    return jsonify({"recommendations": recommended})

# Example of entity interaction endpoints using entity_service - 
# no changes needed here since original code has no such endpoints for this entity.
# If you had local dicts storing entities, you would replace with entity_service calls as per instructions.

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)