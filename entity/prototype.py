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

# In-memory cache for favorites: {userId: set(petId)}
favorites_cache: Dict[str, set] = {}

# In-memory cache for pets search results keyed by request id (simulated)
search_cache: Dict[str, List[Dict]] = {}

# Base URL for Petstore API (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Utility function: fetch pets from external API using filters
async def fetch_pets_from_petstore(
    type_: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            # Petstore API does not support filtering by type or name directly via query params
            # We'll fetch by status if provided, else fetch all available pets (status=available)
            pet_status = status or "available"

            # POST /pet/findByStatus supports only status filtering
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": pet_status})
            r.raise_for_status()
            pets = r.json()

            # Filter by type and name locally
            filtered = []
            for pet in pets:
                if type_ and pet.get("category") and pet["category"].get("name"):
                    if pet["category"]["name"].lower() != type_.lower():
                        continue
                elif type_:
                    # If no category info, skip if type filter present
                    continue

                if name and pet.get("name"):
                    if name.lower() not in pet["name"].lower():
                        continue

                filtered.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name", ""),
                    "status": pet_status,
                    "photoUrls": pet.get("photoUrls", [])
                })
            return filtered
    except Exception as e:
        logger.exception(e)
        return []

# Endpoint: POST /pets/search
@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")
    name = data.get("name")

    pets = await fetch_pets_from_petstore(type_, status, name)
    # TODO: For large result sets, consider pagination (not implemented here)

    # Store last results in cache by timestamp key (simulate request ID)
    request_id = datetime.utcnow().isoformat()
    search_cache[request_id] = pets

    return jsonify({"pets": pets})

# Endpoint: POST /pets/favorites
@app.route("/pets/favorites", methods=["POST"])
async def add_favorite():
    data = await request.get_json(force=True)
    user_id = data.get("userId")
    pet_id = data.get("petId")

    if not user_id or not pet_id:
        return jsonify({"error": "Missing userId or petId"}), 400

    # Add petId to user's favorites set
    user_favs = favorites_cache.setdefault(user_id, set())
    user_favs.add(pet_id)

    return jsonify({"message": "Pet added to favorites"})

# Endpoint: GET /pets/favorites/{userId}
@app.route("/pets/favorites/<user_id>", methods=["GET"])
async def get_favorites(user_id: str):
    user_favs = favorites_cache.get(user_id, set())
    if not user_favs:
        return jsonify({"favorites": []})

    # Fetch pet details for each favorite petId from Petstore API
    pets = []

    async with httpx.AsyncClient() as client:
        for pet_id in user_favs:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                if r.status_code == 200:
                    pet = r.json()
                    pets.append({
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name", ""),
                        "status": pet.get("status", "")
                    })
                else:
                    logger.info(f"Pet id {pet_id} not found in external API")
            except Exception as e:
                logger.exception(e)

    return jsonify({"favorites": pets})

# Endpoint: POST /pets/recommend
@app.route("/pets/recommend", methods=["POST"])
async def recommend_pets():
    data = await request.get_json(force=True)
    user_id = data.get("userId")
    preferences = data.get("preferences", {})

    if not user_id:
        return jsonify({"error": "Missing userId"}), 400

    type_pref = preferences.get("type")
    status_pref = preferences.get("status", "available")

    # Simple recommendation logic:
    # - Fetch pets from Petstore with filters
    # - Exclude pets already in favorites
    # - Return top N (e.g. 5)
    pets = await fetch_pets_from_petstore(type_pref, status_pref, None)
    user_favs = favorites_cache.get(user_id, set())

    recommended = [pet for pet in pets if pet["id"] not in user_favs]

    # Limit recommendations to 5
    recommended = recommended[:5]

    return jsonify({"recommendations": recommended})

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
