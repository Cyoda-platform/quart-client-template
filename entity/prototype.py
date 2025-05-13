```python
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches/mocks
favorite_pets = {}
orders = {}
# Simulate auto-increment IDs for orders
_next_order_id = 1

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper async function to fetch pets from Petstore API based on filters
async def fetch_pets(category: Optional[str], status: Optional[str], name: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient() as client:
        # Petstore API supports findByStatus only, category and name filtering will be done locally
        params = {}
        if status:
            params["status"] = status

        try:
            if status:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
                r.raise_for_status()
                pets = r.json()
            else:
                # If no status filter, fallback to findAll (not supported), so get by available status by default
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
                r.raise_for_status()
                pets = r.json()
        except Exception as e:
            logger.exception(e)
            return []

    # Filter by category and name locally
    def match(p):
        cat_match = True
        name_match = True
        if category:
            cat_match = any(c.get("name", "").lower() == category.lower() for c in p.get("category", {}).values() if isinstance(p.get("category"), dict)) if isinstance(p.get("category"), dict) else (p.get("category", {}).get("name", "").lower() == category.lower())
            # Defensive fallback:
            if isinstance(p.get("category"), dict):
                cat_match = p["category"].get("name", "").lower() == category.lower()
            else:
                cat_match = True  # no category info, don't filter out
        if name:
            name_match = name.lower() in p.get("name", "").lower()
        return cat_match and name_match

    filtered_pets = [p for p in pets if match(p)]
    return filtered_pets

# Helper async function to validate pet existence by ID via Petstore API
async def validate_pet_exists(pet_id: int) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
            return pet
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.exception(e)
            return None
        except Exception as e:
            logger.exception(e)
            return None


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json()
    category = data.get("category")
    status = data.get("status")
    name = data.get("name")

    pets = await fetch_pets(category, status, name)
    # Normalize photoUrls to empty list if missing
    for p in pets:
        if "photoUrls" not in p or not isinstance(p["photoUrls"], list):
            p["photoUrls"] = []
    return jsonify({"pets": pets})


@app.route("/pets/favorite", methods=["POST"])
async def pets_favorite():
    data = await request.get_json()
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"message": "petId must be an integer"}), 400

    pet = await validate_pet_exists(pet_id)
    if not pet:
        return jsonify({"message": f"Pet with id {pet_id} not found"}), 404

    favorite_pets[pet_id] = {
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
async def pets_favorites():
    favorites_list = list(favorite_pets.values())
    return jsonify({"favorites": favorites_list})


@app.route("/pets/order", methods=["POST"])
async def pets_order():
    global _next_order_id
    data = await request.get_json()
    pet_id = data.get("petId")
    quantity = data.get("quantity")
    ship_date = data.get("shipDate")

    if not isinstance(pet_id, int):
        return jsonify({"message": "petId must be an integer"}), 400
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({"message": "quantity must be a positive integer"}), 400

    pet = await validate_pet_exists(pet_id)
    if not pet:
        return jsonify({"message": f"Pet with id {pet_id} not found"}), 404

    if pet.get("status") != "available":
        return jsonify({"message": f"Pet with id {pet_id} is not available"}), 400

    # TODO: In a real app, handle stock and concurrency properly

    order_id = _next_order_id
    _next_order_id += 1

    # Use current time if no shipDate provided
    try:
        ship_date_parsed = datetime.fromisoformat(ship_date) if ship_date else datetime.utcnow()
    except Exception:
        ship_date_parsed = datetime.utcnow()

    order_record = {
        "orderId": order_id,
        "petId": pet_id,
        "quantity": quantity,
        "shipDate": ship_date_parsed.isoformat(),
        "status": "placed"
    }
    orders[order_id] = order_record

    return jsonify(order_record)


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
