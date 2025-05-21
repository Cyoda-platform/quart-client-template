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

# Local in-memory caches to mock persistence — stored inside app context
# Use app.config to hold shared state safely in async environment
app.config["pets_cache"] = []           # Last fetched pets list
app.config["favorites_set"] = set()     # Favorite pet IDs


# Helper: fetch pets from real Petstore API with filters
async def fetch_pets_from_petstore(categories: Optional[List[str]], status: Optional[str], limit: Optional[int]) -> List[Dict]:
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    # Petstore API supports status query param only, no category filter directly
    # We'll filter categories manually after fetch
    params = {"status": status if status else "available"}  # default to "available"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            # Filter by categories if specified
            if categories:
                categories_lower = [c.lower() for c in categories]
                filtered = [
                    pet for pet in pets
                    if pet.get("category") and pet["category"].get("name", "").lower() in categories_lower
                ]
            else:
                filtered = pets

            if limit is not None:
                filtered = filtered[:limit]

            # Normalize pet data shape for our API response
            normalized = []
            for pet in filtered:
                normalized.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls", []),
                    "description": pet.get("tags", [{}])[0].get("name", "")  # Using first tag name as description placeholder
                })
            return normalized
    except httpx.HTTPError as e:
        logger.exception(f"Error fetching pets from Petstore API: {e}")
        return []


# Background task to fetch and cache pets in app.config
async def process_fetch_pets_request(data: Dict):
    try:
        pets = await fetch_pets_from_petstore(
            categories=data.get("categories"),
            status=data.get("status"),
            limit=data.get("limit"),
        )
        app.config["pets_cache"] = pets
        logger.info(f"Fetched and cached {len(pets)} pets.")
    except Exception as e:
        logger.exception(f"Failed to process fetch_pets_request: {e}")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    # Fire and forget the processing task, return accepted immediately
    # TODO: For prototype, we run it inline to show results immediately
    await process_fetch_pets_request(data)
    return jsonify({"pets": app.config["pets_cache"]}), 200


@app.route("/pets/favorites", methods=["POST"])
async def pets_favorites():
    data = await request.get_json(force=True)
    action = data.get("action")
    pet_id = data.get("petId")

    if action not in ("add", "remove") or not isinstance(pet_id, int):
        return jsonify({"error": "Invalid action or petId"}), 400

    if action == "add":
        app.config["favorites_set"].add(pet_id)
    elif action == "remove":
        app.config["favorites_set"].discard(pet_id)

    # Return current favorite pet IDs
    return jsonify({
        "success": True,
        "favorites": list(app.config["favorites_set"])
    })


@app.route("/pets", methods=["GET"])
async def pets_get():
    return jsonify({"pets": app.config["pets_cache"]})


@app.route("/pets/favorites", methods=["GET"])
async def favorites_get():
    # Return detailed info of favorite pets from cached pets data
    fav_ids = app.config["favorites_set"]
    pets = app.config["pets_cache"]
    favorites = [pet for pet in pets if pet["id"] in fav_ids]
    return jsonify({"favorites": favorites})


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
