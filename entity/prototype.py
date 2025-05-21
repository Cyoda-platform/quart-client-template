import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    categories: Optional[List[str]] = None
    status: Optional[str] = None
    limit: Optional[int] = None

@dataclass
class FavoritesRequest:
    action: str
    petId: int

# Helper: fetch pets from real Petstore API with filters
async def fetch_pets_from_petstore(categories: Optional[List[str]], status: Optional[str], limit: Optional[int]) -> List[Dict]:
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    params = {"status": status if status else "available"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
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
            normalized = []
            for pet in filtered:
                normalized.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls", []),
                    "description": pet.get("tags", [{}])[0].get("name", "")
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
@validate_request(FetchPetsRequest)  # workaround: validation last for POST due to quart-schema issue
async def pets_fetch(data: FetchPetsRequest):
    payload = {
        "categories": data.categories,
        "status": data.status,
        "limit": data.limit
    }
    await process_fetch_pets_request(payload)
    return jsonify({"pets": app.config.get("pets_cache", [])}), 200

@app.route("/pets/favorites", methods=["POST"])
@validate_request(FavoritesRequest)  # workaround: validation last for POST due to quart-schema issue
async def pets_favorites(data: FavoritesRequest):
    action = data.action
    pet_id = data.petId
    if action not in ("add", "remove"):
        return jsonify({"error": "Invalid action"}), 400
    if action == "add":
        app.config["favorites_set"].add(pet_id)
    else:
        app.config["favorites_set"].discard(pet_id)
    return jsonify({
        "success": True,
        "favorites": list(app.config.get("favorites_set", set()))
    })

@app.route("/pets", methods=["GET"])
async def pets_get():
    return jsonify({"pets": app.config.get("pets_cache", [])})

@app.route("/pets/favorites", methods=["GET"])
async def favorites_get():
    fav_ids = app.config.get("favorites_set", set())
    pets = app.config.get("pets_cache", [])
    favorites = [pet for pet in pets if pet["id"] in fav_ids]
    return jsonify({"favorites": favorites})

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # initialize mock caches
    app.config["pets_cache"] = []
    app.config["favorites_set"] = set()
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)