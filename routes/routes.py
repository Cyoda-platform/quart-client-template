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

adoption_lock = asyncio.Lock()
adoption_status: Dict[str, str] = {}
PETSTORE_API = "https://petstore.swagger.io/v2"

async def fetch_pet_by_id(pet_id: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_API}/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()
            return pet
    except Exception as e:
        logger.warning(f"Failed to fetch pet {pet_id} from Petstore: {e}")
        return None

async def fetch_pets_by_status(status: str = "available") -> List[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_API}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
            return pets
    except Exception as e:
        logger.warning(f"Failed to fetch pets by status '{status}': {e}")
        return []

# Workflow function for favorite_add_request entity
async def process_favorite_add_request(entity: dict) -> dict:
    pet_id = entity.get("pet_id")
    if not pet_id:
        raise ValueError("pet_id is required in favorite_add_request entity")

    pet = await fetch_pet_by_id(pet_id)
    if not pet:
        raise ValueError(f"Pet with id {pet_id} not found")

    pet_info = {
        "id": str(pet.get("id")),
        "name": pet.get("name", ""),
        "type": pet.get("category", {}).get("name", "").lower() if pet.get("category") else "",
        "breed": "",  # Petstore does not provide breed info
        "age": 0,     # Petstore does not provide age info
        "status": adoption_status.get(str(pet.get("id")), "available"),
    }
    entity["pet_info"] = pet_info
    now_iso = datetime.utcnow().isoformat() + "Z"
    entity["added_at"] = now_iso
    entity["processed_at"] = now_iso
    return entity

# Workflow function for adopt_request entity
async def process_adopt_request(entity: dict) -> dict:
    pet_id = entity.get("petId")
    user_name = entity.get("userName")
    if not pet_id or not user_name:
        raise ValueError("petId and userName are required in adopt_request entity")

    async with adoption_lock:
        current_status = adoption_status.get(pet_id, "available")
        if current_status != "available":
            entity["adoption_success"] = False
            entity["message"] = "Pet is not available for adoption."
            logger.info(f"Adoption failed: pet {pet_id} already adopted")
        else:
            adoption_status[pet_id] = "adopted"
            entity["adoption_success"] = True
            entity["message"] = "Adoption request confirmed."
            entity["adopted_at"] = datetime.utcnow().isoformat() + "Z"
            logger.info(f"User '{user_name}' adopted pet {pet_id}")

    return entity

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    pets = await fetch_pets_by_status("available")

    filtered = []
    type_lower = data.type.lower() if data.type else None
    name_lower = data.name.lower() if data.name else None
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
        pet_name = pet.get("name", "").lower()
        if type_lower and type_lower != pet_type:
            continue
        if name_lower and name_lower not in pet_name:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type,
            "breed": "",
            "age": 0,
            "status": adoption_status.get(str(pet.get("id")), "available"),
        })
    return jsonify({"pets": filtered})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)
async def pets_adopt(data: AdoptRequest):
    entity = {"petId": data.petId, "userName": data.userName}
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adopt_request",
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        if entity.get("adoption_success"):
            return jsonify({"success": True, "message": entity.get("message", "")})
        else:
            return jsonify({"success": False, "message": entity.get("message", "")}), 409
    except Exception as e:
        logger.exception(f"Error in adopt endpoint: {e}")
        return jsonify({"success": False, "message": "Adoption failed due to server error."}), 500

@app.route("/pets/favorites/add", methods=["POST"])
@validate_request(FavoriteAddRequest)
async def pets_favorites_add(data: FavoriteAddRequest):
    entity = {"pet_id": data.petId, "user_name": data.userName}
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite_add_request",
            entity_version=ENTITY_VERSION,
            entity=entity
        )
        return jsonify({"success": True, "id": id_})
    except Exception as e:
        logger.exception(f"Error in favorites add endpoint: {e}")
        return jsonify({"success": False, "message": "Failed to add favorite."}), 500

@validate_querystring(FavoritesQuery)
@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    user_name = request.args.get("userName")
    try:
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
        logger.exception(f"Error fetching favorites: {e}")
        return jsonify({"favorites": []}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
