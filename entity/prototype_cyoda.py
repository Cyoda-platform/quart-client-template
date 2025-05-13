import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

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

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

@dataclass
class SearchPetsRequest:
    category: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class FavoritePetRequest:
    pet_id: str  # changed to string for id

@dataclass
class OrderPetRequest:
    pet_id: str  # changed to string for id
    quantity: int
    ship_date: Optional[str] = None

async def fetch_pets(category: Optional[str], status: Optional[str], name: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient() as client:
        params = {}
        if status:
            params["status"] = status
        try:
            if status:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
                r.raise_for_status()
                pets = r.json()
            else:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
                r.raise_for_status()
                pets = r.json()
        except Exception as e:
            logger.exception(e)
            return []
    def match(p):
        cat_match = True
        name_match = True
        if category:
            cat = p.get("category", {}).get("name", "")
            cat_match = cat.lower() == category.lower()
        if name:
            name_match = name.lower() in p.get("name", "").lower()
        return cat_match and name_match
    return [p for p in pets if match(p)]

async def validate_pet_exists(pet_id: str) -> Optional[dict]:
    # pet_id is string now
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        return pet
    except Exception as e:
        # fallback to external API check if not found in entity_service or error
        if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 404:
            return None
        # fallback to external petstore check
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as ex:
                if ex.response.status_code == 404:
                    return None
                logger.exception(ex)
                return None
            except Exception as ex:
                logger.exception(ex)
                return None

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPetsRequest)
async def pets_search(data: SearchPetsRequest):
    pets = await fetch_pets(data.category, data.status, data.name)
    for p in pets:
        if "photoUrls" not in p or not isinstance(p["photoUrls"], list):
            p["photoUrls"] = []
    return jsonify({"pets": pets})

@app.route("/pets/favorite", methods=["POST"])
@validate_request(FavoritePetRequest)
async def pets_favorite(data: FavoritePetRequest):
    pet = await validate_pet_exists(str(data.pet_id))
    if not pet:
        return jsonify({"message": f"Pet with id {data.pet_id} not found"}), 404
    # add favorite pet via entity_service
    favorite_pet_data = {
        "id": pet["id"],
        "name": pet["name"],
        "category": pet.get("category", {}),
        "status": pet.get("status", "")
    }
    try:
        favorite_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite_pet",
            entity_version=ENTITY_VERSION,
            entity=favorite_pet_data
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to add favorite pet"}), 500
    return jsonify({
        "message": "Pet added to favorites",
        "favoritePet": {
            "id": pet["id"],
            "name": pet["name"]
        }
    })

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    try:
        favorites = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="favorite_pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        favorites = []
    return jsonify({"favorites": favorites})

@app.route("/pets/order", methods=["POST"])
@validate_request(OrderPetRequest)
async def pets_order(data: OrderPetRequest):
    pet_id_str = str(data.pet_id)
    pet = await validate_pet_exists(pet_id_str)
    if not pet:
        return jsonify({"message": f"Pet with id {data.pet_id} not found"}), 404
    if pet.get("status") != "available":
        return jsonify({"message": f"Pet with id {data.pet_id} is not available"}), 400

    try:
        ship_date_parsed = datetime.fromisoformat(data.ship_date) if data.ship_date else datetime.utcnow()
    except Exception:
        ship_date_parsed = datetime.utcnow()

    order_record = {
        "petId": pet_id_str,
        "quantity": data.quantity,
        "shipDate": ship_date_parsed.isoformat(),
        "status": "placed"
    }
    try:
        order_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_record
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to place order"}), 500

    return jsonify({"orderId": order_id})

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)