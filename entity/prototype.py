```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "persistence" caches - asyncio-safe by using asyncio.Lock
favorites_lock = asyncio.Lock()
favorites_cache: Dict[str, List[int]] = {}

reviews_lock = asyncio.Lock()
reviews_cache: Dict[int, List[Dict]] = {}

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(criteria: dict) -> List[dict]:
    """Query the external Petstore API /pet/findByStatus endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Petstore API supports multiple statuses as CSV, we support one status here
            status = criteria.get("status", "")
            # TODO: extend filtering by type locally as Petstore API does not support filtering by type
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            response = await client.get(url, params={"status": status})
            response.raise_for_status()
            pets = response.json()
            # Filter by type if provided (locally)
            pet_type = criteria.get("type")
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
    except Exception as e:
        logger.exception(f"Failed fetching pets from Petstore: {e}")
        return []


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    try:
        criteria = await request.get_json()
        pets = await fetch_pets_from_petstore(criteria)
        # Simplify response to match functional spec
        result = []
        for pet in pets:
            result.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", []),
            })
        return jsonify({"pets": result})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/favorite", methods=["POST"])
async def add_favorite_pet():
    try:
        data = await request.get_json()
        user_id = data.get("userId")
        pet_id = data.get("petId")
        if not user_id or not pet_id:
            return jsonify({"error": "userId and petId are required"}), 400

        async with favorites_lock:
            user_favs = favorites_cache.setdefault(user_id, [])
            if pet_id not in user_favs:
                user_favs.append(pet_id)

        return jsonify({"message": "Pet added to favorites"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/favorites/<string:user_id>", methods=["GET"])
async def get_favorite_pets(user_id):
    try:
        async with favorites_lock:
            pet_ids = favorites_cache.get(user_id, []).copy()

        # We need to fetch details for each pet from Petstore API (batch not supported, so do sequential)
        pets = []
        async with httpx.AsyncClient(timeout=10) as client:
            for pet_id in pet_ids:
                try:
                    res = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                    if res.status_code == 200:
                        pet = res.json()
                        pets.append({
                            "id": pet.get("id"),
                            "name": pet.get("name"),
                            "type": pet.get("category", {}).get("name"),
                            "status": pet.get("status"),
                        })
                    else:
                        logger.warning(f"Pet id={pet_id} not found in Petstore")
                except Exception as e:
                    logger.exception(f"Error fetching pet id={pet_id}: {e}")

        return jsonify({"favorites": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/review", methods=["POST"])
async def submit_pet_review():
    try:
        data = await request.get_json()
        user_id = data.get("userId")
        pet_id = data.get("petId")
        rating = data.get("rating")
        comment = data.get("comment", "")

        if not user_id or not pet_id or rating is None:
            return jsonify({"error": "userId, petId and rating are required"}), 400
        if not (1 <= rating <= 5):
            return jsonify({"error": "rating must be between 1 and 5"}), 400

        review = {
            "userId": user_id,
            "rating": rating,
            "comment": comment,
            "submittedAt": datetime.utcnow().isoformat() + "Z",
        }

        async with reviews_lock:
            pet_reviews = reviews_cache.setdefault(pet_id, [])
            pet_reviews.append(review)

        return jsonify({"message": "Review submitted"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/reviews/<int:pet_id>", methods=["GET"])
async def get_pet_reviews(pet_id):
    try:
        async with reviews_lock:
            pet_reviews = reviews_cache.get(pet_id, []).copy()
        return jsonify({"reviews": pet_reviews})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
