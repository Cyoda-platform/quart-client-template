```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches (async safe by design with asyncio tasks)
pets_cache: Dict[int, Dict[str, Any]] = {}
orders_cache: Dict[int, Dict[str, Any]] = {}
order_id_seq = 1
lock = asyncio.Lock()  # to safely increment order_id_seq


PETSTORE_BASE = "https://petstore.swagger.io/v2"


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    """
    POST /pets/search
    Request JSON:
    {
        "type": "cat" (optional),
        "status": "available" (optional),
        "tags": ["tag1", "tag2"] (optional)
    }
    Response JSON:
    {
        "pets": [...]
    }
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")
    tags_filter = set(data.get("tags") or [])

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status or "available"})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"pets": []}), 503

    # Filter by type and tags client side (Petstore API does not support filtering by type/tags)
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

    # Cache pets for GET retrieval
    for pet in filtered_pets:
        pets_cache[pet["id"]] = pet

    return jsonify({"pets": filtered_pets})


@app.route("/pets/order", methods=["POST"])
async def place_order():
    """
    POST /pets/order
    Request JSON:
    {
      "petId": integer,
      "quantity": integer
    }
    Response JSON:
    {
      "orderId": integer,
      "petId": integer,
      "quantity": integer,
      "status": "placed"
    }
    """
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    quantity = data.get("quantity")

    if not isinstance(pet_id, int) or not isinstance(quantity, int) or quantity <= 0:
        abort(400, "Invalid petId or quantity")

    # Verify pet exists in cache or fetch it
    pet = pets_cache.get(pet_id)
    if not pet:
        # Try fetching from Petstore API (fallback)
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

    global order_id_seq
    async with lock:
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
    """
    GET /pets/{petId}
    Response JSON:
    {
      "id": integer,
      "name": string,
      "type": string,
      "status": string,
      "tags": [string]
    }
    """
    pet = pets_cache.get(pet_id)
    if not pet:
        abort(404, "Pet not found in cache")
    return jsonify(pet)


@app.route("/orders/<int:order_id>", methods=["GET"])
async def get_order(order_id: int):
    """
    GET /orders/{orderId}
    Response JSON:
    {
      "orderId": integer,
      "petId": integer,
      "quantity": integer,
      "status": string
    }
    """
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
    import logging

    # Setup logging to stdout
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
