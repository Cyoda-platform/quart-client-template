import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches/mocks
favorite_pets = {}
orders = {}
_next_order_id = 1

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

@dataclass
class SearchPetsRequest:
    category: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class FavoritePetRequest:
    petId: int

@dataclass
class OrderPetRequest:
    petId: int
    quantity: int
    shipDate: Optional[str] = None

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

async def validate_pet_exists(pet_id: int) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.exception(e)
            return None
        except Exception as e:
            logger.exception(e)
            return None

@app.route("/pets/search", methods=["POST"])
# workaround: validate_request must come after route decorator for POST due to quart-schema defect
@validate_request(SearchPetsRequest)
async def pets_search(data: SearchPetsRequest):
    pets = await fetch_pets(data.category, data.status, data.name)
    for p in pets:
        if "photoUrls" not in p or not isinstance(p["photoUrls"], list):
            p["photoUrls"] = []
    return jsonify({"pets": pets})

@app.route("/pets/favorite", methods=["POST"])
# workaround: validate_request must come after route decorator for POST due to quart-schema defect
@validate_request(FavoritePetRequest)
async def pets_favorite(data: FavoritePetRequest):
    pet = await validate_pet_exists(data.petId)
    if not pet:
        return jsonify({"message": f"Pet with id {data.petId} not found"}), 404
    favorite_pets[data.petId] = {
        "id": pet["id"],
        "name": pet["name"],
        "category": pet.get("category", {}),
        "status": pet.get("status", "")
    }
    return jsonify({
        "message": "Pet added to favorites",
        "favoritePet": {
            "id": pet["id"],
            "name": pet["name"]
        }
    })

@app.route("/pets/favorites", methods=["GET"])
# no validation needed for GET without parameters
async def pets_favorites():
    return jsonify({"favorites": list(favorite_pets.values())})

@app.route("/pets/order", methods=["POST"])
# workaround: validate_request must come after route decorator for POST due to quart-schema defect
@validate_request(OrderPetRequest)
async def pets_order(data: OrderPetRequest):
    global _next_order_id
    pet = await validate_pet_exists(data.petId)
    if not pet:
        return jsonify({"message": f"Pet with id {data.petId} not found"}), 404
    if pet.get("status") != "available":
        return jsonify({"message": f"Pet with id {data.petId} is not available"}), 400
    order_id = _next_order_id
    _next_order_id += 1
    try:
        ship_date_parsed = datetime.fromisoformat(data.shipDate) if data.shipDate else datetime.utcnow()
    except Exception:
        ship_date_parsed = datetime.utcnow()
    order_record = {
        "orderId": order_id,
        "petId": data.petId,
        "quantity": data.quantity,
        "shipDate": ship_date_parsed.isoformat(),
        "status": "placed"
    }
    orders[order_id] = order_record
    return jsonify(order_record)

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)