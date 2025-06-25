import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for validation
@dataclass
class SearchRequest:
    type: str = None
    breed: str = None
    name: str = None

@dataclass
class AdoptRequest:
    petId: str
    userName: str

@dataclass
class FavoriteAddRequest:
    petId: str
    userName: str

@dataclass
class FavoritesQuery:
    userName: str

# In-memory async-safe cache for favorites and adoption status
favorites_lock = asyncio.Lock()
favorites_cache: Dict[str, List[Dict]] = {}
adoption_lock = asyncio.Lock()
adoption_status: Dict[str, str] = {}
PETSTORE_API = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(
    type_: str = None, breed: str = None, name: str = None
) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_API}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore: {e}")
        return []
    filtered = []
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower()
        pet_name = pet.get("name", "").lower()
        if type_ and type_.lower() != pet_type:
            continue
        if name and name.lower() not in pet_name:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type,
            "breed": "",  # TODO: breed info not available
            "age": 0,     # TODO: age info not available
            "status": adoption_status.get(str(pet.get("id")), "available"),
        })
    return filtered

async def adopt_pet(pet_id: str, user_name: str) -> bool:
    async with adoption_lock:
        current = adoption_status.get(pet_id, "available")
        if current != "available":
            return False
        adoption_status[pet_id] = "adopted"
    logger.info(f"User '{user_name}' adopted pet {pet_id}")
    return True

async def add_favorite_pet(pet_id: str, user_name: str, pet_info: Dict) -> None:
    async with favorites_lock:
        favs = favorites_cache.setdefault(user_name, [])
        if not any(f["id"] == pet_id for f in favs):
            favs.append(pet_info)
            logger.info(f"Pet {pet_id} added to favorites for user '{user_name}'")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)  # validation last for POST due to defect
async def pets_search(data: SearchRequest):
    pets = await fetch_pets_from_petstore(data.type, data.breed, data.name)
    return jsonify({"pets": pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)  # validation last for POST due to defect
async def pets_adopt(data: AdoptRequest):
    success = await adopt_pet(data.petId, data.userName)
    if success:
        return jsonify({"success": True, "message": "Adoption request confirmed."})
    return jsonify({"success": False, "message": "Pet is not available for adoption."}), 409

@app.route("/pets/favorites/add", methods=["POST"])
@validate_request(FavoriteAddRequest)  # validation last for POST due to defect
async def pets_favorites_add(data: FavoriteAddRequest):
    pets = await fetch_pets_from_petstore()
    pet_info = next((p for p in pets if p["id"] == data.petId), None)
    if not pet_info:
        return jsonify({"success": False, "message": "Pet not found"}), 404
    await add_favorite_pet(data.petId, data.userName, pet_info)
    return jsonify({"success": True, "message": "Pet added to favorites."})

# workaround: validation first for GET due to quart-schema defect
@validate_querystring(FavoritesQuery)
@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    user_name = request.args.get("userName")
    async with favorites_lock:
        favs = favorites_cache.get(user_name, [])
    return jsonify({"favorites": favs})

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)