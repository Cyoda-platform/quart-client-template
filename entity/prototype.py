from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@dataclass
class OrderRequest:
    petId: int
    quantity: int

# In-memory caches (async safe by design with asyncio tasks)
pets_cache: Dict[int, Dict[str, Any]] = {}
orders_cache: Dict[int, Dict[str, Any]] = {}
order_id_seq = 1
lock = asyncio.Lock()

PETSTORE_BASE = "https://petstore.swagger.io/v2"

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)  # Workaround: POST validation decorator placed last due to quart-schema issue
async def search_pets(data: PetSearch):
    pet_type = data.type
    status = data.status
    tags_filter = set(data.tags or [])

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status or "available"})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"pets": []}), 503

    def pet_matches(pet):
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            return False
        if tags_filter:
            pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
            if not tags_filter.issubset(pet_tags):
                return False
        return True

    filtered_pets = [
        {
            "id": pet["id"],
            "name": pet.get("name", ""),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "tags": [tag.get("name", "") for tag in pet.get("tags", [])]
        }
        for pet in pets if pet_matches(pet)
    ]

    for pet in filtered_pets:
        pets_cache[pet["id"]] = pet

    return jsonify({"pets": filtered_pets})

@app.route("/pets/order", methods=["POST"])
@validate_request(OrderRequest)  # Workaround: POST validation decorator placed last due to quart-schema issue
async def place_order(data: OrderRequest):
    pet_id = data.petId
    quantity = data.quantity

    if quantity <= 0:
        abort(400, "Invalid quantity")

    pet = pets_cache.get(pet_id)
    if not pet:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}")
                resp.raise_for_status()
                pet_data = resp.json()
                pet = {
                    "id": pet_data["id"],
                    "name": pet_data.get("name", ""),
                    "type": pet_data.get("category", {}).get("name", ""),
                    "status": pet_data.get("status", ""),
                    "tags": [tag.get("name", "") for tag in pet_data.get("tags", [])]
                }
                pets_cache[pet_id] = pet
            except Exception as e:
                logger.exception(e)
                abort(404, "Pet not found")

    async with lock:
        global order_id_seq
        current_order_id = order_id_seq
        order_id_seq += 1

    order = {
        "orderId": current_order_id,
        "petId": pet_id,
        "quantity": quantity,
        "status": "placed",
        "placedAt": datetime.utcnow().isoformat() + "Z"
    }
    orders_cache[current_order_id] = order

    return jsonify({
        "orderId": order["orderId"],
        "petId": order["petId"],
        "quantity": order["quantity"],
        "status": order["status"]
    })

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        abort(404, "Pet not found in cache")
    return jsonify(pet)

@app.route("/orders/<int:order_id>", methods=["GET"])
async def get_order(order_id: int):
    order = orders_cache.get(order_id)
    if not order:
        abort(404, "Order not found")
    return jsonify({
        "orderId": order["orderId"],
        "petId": order["petId"],
        "quantity": order["quantity"],
        "status": order["status"]
    })

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)