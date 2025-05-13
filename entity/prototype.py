```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches for pets and orders (simulate persistence)
pets_cache: Dict[int, Dict[str, Any]] = {}
orders_cache: Dict[int, Dict[str, Any]] = {}

PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Order ID generator helper (async safe by design of single-thread event loop)
order_id_counter = 1000


async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch pets from Petstore API using given filters.
    Petstore API supports filtering by status only, others filtered locally.
    """
    status = filters.get("status")
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status or "available,pending,sold"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed fetching pets from Petstore API")
            pets = []

    # Local filtering for category and name
    category_filter = filters.get("category", "").lower()
    name_filter = filters.get("name", "").lower()

    def matches(pet):
        if category_filter:
            cat = pet.get("category", {}).get("name", "").lower()
            if cat != category_filter:
                return False
        if name_filter:
            if name_filter not in (pet.get("name") or "").lower():
                return False
        return True

    filtered = [pet for pet in pets if matches(pet)]

    # Normalize and cache pets locally
    result_pets = []
    for pet in filtered:
        pet_obj = {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        }
        pets_cache[pet_obj["id"]] = pet_obj
        result_pets.append(pet_obj)

    return {"pets": result_pets}


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    try:
        filters = await request.get_json() or {}
    except Exception:
        filters = {}

    result = await fetch_pets_from_petstore(filters)
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
        except Exception as e:
            logger.exception("Error placing order to Petstore")
            return {"error": "Petstore order placement failed"}


@app.route("/orders", methods=["POST"])
async def orders_place():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing order data"}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Generate order id locally (no global keyword, use app context)
    # TODO: For concurrency, consider a better id generator if scaling
    order_id = len(orders_cache) + 1001

    order_payload = {
        "id": order_id,
        "petId": data.get("petId"),
        "quantity": data.get("quantity", 1),
        "shipDate": data.get("shipDate"),
        "status": data.get("status", "placed"),
        "complete": data.get("complete", False),
    }

    # Fire and forget pattern to simulate async processing if needed
    entity_job = {order_id: {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}}
    
    async def process_order(job: Dict[int, Dict[str, Any]], order_data: Dict[str, Any]):
        try:
            petstore_resp = await place_order_petstore(order_data)
            if "error" in petstore_resp:
                job[order_data["id"]]["status"] = "failed"
                logger.error(f"Order {order_data['id']} failed in Petstore: {petstore_resp['error']}")
            else:
                job[order_data["id"]]["status"] = "completed"
                # Cache order locally on success
                orders_cache[order_data["id"]] = order_data
        except Exception as e:
            job[order_data["id"]]["status"] = "failed"
            logger.exception(f"Exception processing order {order_data['id']}: {e}")
    
    await asyncio.create_task(process_order(entity_job, order_payload))

    # Return optimistic success, real status can be checked later (TODO: add status endpoint if needed)
    return jsonify({
        "orderId": order_id,
        "status": "placed",
        "message": "Order successfully placed"
    })


@app.route("/orders/<int:order_id>", methods=["GET"])
async def orders_get(order_id: int):
    order = orders_cache.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```