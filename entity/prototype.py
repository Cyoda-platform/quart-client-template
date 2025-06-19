```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for pets data and adoption status keyed by pet id
# Structure:
# pets_store = {
#   pet_id: {
#       "id": int,
#       "name": str,
#       "category": str,
#       "status": str,
#       ...
#   }
# }
pets_store: Dict[int, Dict] = {}

# Lock to protect pets_store access in async environment
pets_store_lock = asyncio.Lock()

# External Petstore API base URL
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(status: Optional[str], category: Optional[str]) -> List[Dict]:
    """Fetch pets from external Petstore API filtered by status and category.
    Filters by category will be applied locally as external API does not support category filtering."""
    try:
        async with httpx.AsyncClient() as client:
            # Petstore API supports querying pets by status only:
            # GET /pet/findByStatus?status={status}
            # If no status provided, fetch all statuses (available, pending, sold)
            query_status = status if status else "available,pending,sold"
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            response = await client.get(url, params={"status": query_status})
            response.raise_for_status()
            pets = response.json()
            # Filter locally by category if provided
            if category:
                category_lower = category.lower()
                pets = [
                    pet for pet in pets
                    if pet.get("category", {}).get("name", "").lower() == category_lower
                ]
            return pets
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore API: {e}")
        return []

async def store_pets(pets: List[Dict]):
    """Store fetched pets into the in-memory pets_store asynchronously."""
    async with pets_store_lock:
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id is not None:
                # Normalize pet data with fields we use later
                pets_store[pet_id] = {
                    "id": pet_id,
                    "name": pet.get("name", ""),
                    "category": pet.get("category", {}).get("name", ""),
                    "status": pet.get("status", ""),
                }

async def adopt_pet(pet_id: int) -> Optional[Dict]:
    """Mark pet as adopted (status = sold) in local store.
    TODO: Optionally update external Petstore API if supported."""
    async with pets_store_lock:
        pet = pets_store.get(pet_id)
        if not pet:
            return None
        pet["status"] = "sold"
        # TODO: Implement external Petstore API update if available.
        return pet

@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    try:
        data = await request.get_json(force=True)
        status = data.get("status")
        category = data.get("category")

        requested_at = datetime.utcnow().isoformat()
        logger.info(f"Received fetch request at {requested_at} with status={status} category={category}")

        # Fire and forget processing task to fetch and store pets
        # Return immediately with processing message
        async def process_fetch():
            pets = await fetch_pets_from_petstore(status, category)
            await store_pets(pets)
            logger.info(f"Fetched and stored {len(pets)} pets from Petstore API")

        asyncio.create_task(process_fetch())

        return jsonify({
            "message": "Pets data fetch started asynchronously.",
            "requestedAt": requested_at
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process fetch request"}), 500

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        # Filters and pagination via query params
        status = request.args.get("status")
        category = request.args.get("category")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))

        async with pets_store_lock:
            pets_list = list(pets_store.values())

        if status:
            status_lower = status.lower()
            pets_list = [p for p in pets_list if p["status"].lower() == status_lower]
        if category:
            category_lower = category.lower()
            pets_list = [p for p in pets_list if p["category"].lower() == category_lower]

        total = len(pets_list)
        pets_page = pets_list[offset: offset + limit]

        return jsonify({
            "pets": pets_page,
            "total": total,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/adopt", methods=["POST"])
async def adopt():
    try:
        data = await request.get_json(force=True)
        pet_id = data.get("petId")
        if not isinstance(pet_id, int):
            return jsonify({"error": "petId must be an integer"}), 400

        pet = await adopt_pet(pet_id)
        if not pet:
            return jsonify({"error": f"Pet with id {pet_id} not found"}), 404

        return jsonify({
            "message": f"Pet {pet_id} adopted successfully.",
            "pet": pet
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to adopt pet"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
