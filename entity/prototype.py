from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches
pets_cache: Dict[int, Dict[str, Any]] = {}
orders_cache: Dict[int, Dict[str, Any]] = {}

PETSTORE_BASE = "https://petstore.swagger.io/v2"

@dataclass
class PetSearchFilters:
    status: str = None
    category: str = None
    name: str = None

@dataclass
class OrderRequest:
    petId: int
    quantity: int
    shipDate: str
    status: str
    complete: bool

async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": filters.get("status") or "available,pending,sold"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed fetching pets from Petstore API")
            pets = []
    cat_f = (filters.get("category") or "").lower()
    name_f = (filters.get("name") or "").lower()
    def matches(pet):
        if cat_f:
            if (pet.get("category") or {}).get("name", "").lower() != cat_f:
                return False
        if name_f:
            if name_f not in (pet.get("name") or "").lower():
                return False
        return True
    filtered = [pet for pet in pets if matches(pet)]
    result = []
    for pet in filtered:
        pet_obj = {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
            "tags": [t.get("name") for t in pet.get("tags", [])] if pet.get("tags") else []
        }
        pets_cache[pet_obj["id"]] = pet_obj
        result.append(pet_obj)
    return {"pets": result}

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchFilters)  # workaround: validate_request must be last on POST
async def pets_search(filters: PetSearchFilters):
    result = await fetch_pets_from_petstore(filters.__dict__)
    return jsonify(result)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_details(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

async def place_order_petstore(order: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{PETSTORE_BASE}/store/order"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=order, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception("Error placing order to Petstore")
            return {"error": "Petstore order placement failed"}

@app.route("/orders", methods=["POST"])
@validate_request(OrderRequest)  # workaround: validate_request must be last on POST
async def orders_place(data: OrderRequest):
    order_id = len(orders_cache) + 1001
    order_payload = {
        "id": order_id,
        "petId": data.petId,
        "quantity": data.quantity,
        "shipDate": data.shipDate,
        "status": data.status,
        "complete": data.complete,
    }
    entity_job = {order_id: {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}}
    async def process_order(job: Dict[int, Dict[str, Any]], od: Dict[str, Any]):
        try:
            resp = await place_order_petstore(od)
            if "error" in resp:
                job[od["id"]]["status"] = "failed"
                logger.error(f"Order {od['id']} failed: {resp['error']}")
            else:
                job[od["id"]]["status"] = "completed"
                orders_cache[od["id"]] = od
        except Exception as e:
            job[od["id"]]["status"] = "failed"
            logger.exception(e)
    await asyncio.create_task(process_order(entity_job, order_payload))
    return jsonify({"orderId": order_id, "status": "placed", "message": "Order successfully placed"})

@app.route("/orders/<int:order_id>", methods=["GET"])
async def orders_get(order_id: int):
    order = orders_cache.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)