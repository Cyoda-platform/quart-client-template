import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

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

# In-memory async-safe cache for adoption status only (favorites will be stored externally)
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

# Refactor favorites to use entity_service instead of in-memory cache
@app.route("/pets/favorites/add", methods=["POST"])
@validate_request(FavoriteAddRequest)  # validation last for POST due to defect
async def pets_favorites_add(data: FavoriteAddRequest):
    # First, fetch pet info from petstore (as before)
    pets = await fetch_pets_from_petstore()
    pet_info = next((p for p in pets if p["id"] == data.petId), None)
    if not pet_info:
        return jsonify({"success": False, "message": "Pet not found"}), 404

    # Prepare favorite entity data
    favorite_entity = {
        "pet_id": data.petId,
        "user_name": data.userName,
        "pet_info": pet_info,
        "added_at": datetime.utcnow().isoformat() + "Z"
    }
    try:
        # Add favorite item asynchronously
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite_add_request",
            entity_version=ENTITY_VERSION,
            entity=favorite_entity
        )
        # Return only the id, the favorite data must be retrieved separately
        return jsonify({"success": True, "id": id_})
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Failed to add favorite."}), 500

# workaround: validation first for GET due to quart-schema defect
@validate_querystring(FavoritesQuery)
@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    user_name = request.args.get("userName")
    try:
        # Condition to get favorites by user_name
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.user_name",
                        "operatorType": "EQUALS",
                        "value": user_name,
                        "type": "simple"
                    }
                ]
            }
        }
        favorites = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="favorite_add_request",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify({"favorites": favorites})
    except Exception as e:
        logger.exception(e)
        return jsonify({"favorites": []}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)