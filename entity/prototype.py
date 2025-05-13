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

# Local in-memory caches for pets and orders, keyed by id (simulate persistence)
pets_cache: Dict[int, Dict[str, Any]] = {}
orders_cache: Dict[int, Dict[str, Any]] = {}

PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Helper to generate order IDs locally
_order_id_seq = 1000


async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch pets from Petstore API using given filters.
    Petstore API does not support complex search, so we do basic status filter and then filter in app.
    """
    status = filters.get("status")
    # Petstore supports GET /pet/findByStatus?status=available
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    else:
        # Default to all statuses supported by Petstore API
        params["status"] = "available,pending,sold"

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore: {e}")
            pets = []

    # Filter by category and name locally
    category_filter = filters.get("category", "").lower()
    name_filter = filters.get("name", "").lower()

    def pet_matches(pet):
        if category_filter:
            if not pet.get("category") or pet["category"].get("name", "").lower() != category_filter:
                return False
        if name_filter:
            if name_filter not in (pet.get("name") or "").lower():
                return False
        return True

    filtered_pets = [pet for pet in pets if pet_matches(pet)]

    # Normalize pets to our response format and update local cache
    result_pets = []
    for pet in filtered_pets:
        pet_obj = {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else []
        }
        # Cache pet locally for GET /pets/{petId}
        pets_cache[pet_obj["id"]] = pet_obj
        result_pets.append(pet_obj)

    return {"pets": result_pets}


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    """
    POST /pets/search
    Body: JSON with optional filters: status, category, name
    Returns filtered pet list from Petstore API
    """
    try:
        filters = await request.get_json()
        if filters is None:
            filters = {}
    except Exception:
        filters = {}

    result = await fetch_pets_from_petstore(filters)
    return jsonify(result)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet_details(pet_id: int):
    """
    GET /pets/{petId}
    Returns pet details from local cache.
    """
    pet = pets_cache.get(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


async def place_order_to_petstore(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends the order to Petstore API /store/order endpoint.
    Returns the Petstore response or error.
    """
    url = f"{PETSTORE_BASE}/store/order"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=order_data, timeout=10)
            r.raise_for_status()
            resp = r.json()
            return resp
        except Exception as e:
            logger.exception(f"Error placing order to Petstore: {e}")
            return {"error": "Failed to place order with Petstore"}


@app.route("/orders", methods=["POST"])
async def place_order():
    """
    POST /orders
    Body: JSON with petId, quantity, shipDate, status, complete
    Places order in Petstore API, caches result locally.
    """
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing order data"}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    global _order_id_seq
    _order_id_seq += 1
    order_id = _order_id_seq

    # Construct order payload for Petstore API
    order_payload = {
        "id": order_id,
        "petId": data.get("petId"),
        "quantity": data.get("quantity", 1),
        "shipDate": data.get("shipDate"),
        "status": data.get("status", "placed"),
        "complete": data.get("complete", False),
    }

    # Fire and forget placing order to Petstore API, but await result here to return response
    petstore_response = await place_order_to_petstore(order_payload)

    # If error on Petstore side, do not cache order
    if "error" in petstore_response:
        return jsonify({"error": petstore_response["error"]}), 502

    # Cache order locally
    orders_cache[order_id] = order_payload

    return jsonify({
        "orderId": order_id,
        "status": order_payload["status"],
        "message": "Order successfully placed"
    })


@app.route("/orders/<int:order_id>", methods=["GET"])
async def get_order(order_id: int):
    """
    GET /orders/{orderId}
    Returns order details from local cache.
    """
    order = orders_cache.get(order_id)
    if order is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)


if __name__ == '__main__':
    # Run the app on all interfaces, port 8000, debug True, threaded True
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
