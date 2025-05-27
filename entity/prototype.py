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

# In-memory local cache (per app instance) for prototype (async safe-ish with asyncio.Lock)
class LocalCache:
    def __init__(self):
        self._pets: Dict[int, dict] = {}
        self._pet_details: Dict[int, dict] = {}
        self._favorites: set = set()
        self._lock = asyncio.Lock()

    async def store_pets(self, pets: List[dict]):
        async with self._lock:
            for pet in pets:
                self._pets[pet["id"]] = pet

    async def get_pets(self) -> List[dict]:
        async with self._lock:
            return list(self._pets.values())

    async def store_pet_detail(self, pet: dict):
        async with self._lock:
            self._pet_details[pet["id"]] = pet

    async def get_pet_detail(self, pet_id: int) -> Optional[dict]:
        async with self._lock:
            return self._pet_details.get(pet_id)

    async def add_favorite(self, pet_id: int):
        async with self._lock:
            self._favorites.add(pet_id)

    async def get_favorites(self) -> List[dict]:
        async with self._lock:
            return [self._pets[pid] for pid in self._favorites if pid in self._pets]


cache = LocalCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(status: Optional[str] = None) -> List[dict]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
            # Normalize pets to minimal required fields for list view
            normalized = []
            for pet in pets:
                normalized.append(
                    {
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "category": pet.get("category", {}).get("name") if pet.get("category") else None,
                        "status": pet.get("status"),
                    }
                )
            return normalized
        except Exception as e:
            logger.exception("Error fetching pets from Petstore")
            raise e


async def fetch_pet_detail_from_petstore(pet_id: int) -> dict:
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            pet = r.json()
            # Return as-is, but ensure keys present for our API responses
            return pet
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Pet not found
                return {}
            logger.exception(f"Error fetching pet details for id={pet_id}")
            raise e


@app.route("/pets/fetch", methods=["POST"])
async def post_pets_fetch():
    data = await request.get_json(force=True)
    status = data.get("status") if data else None
    try:
        pets = await fetch_pets_from_petstore(status)
        await cache.store_pets(pets)
        return jsonify({"message": "Pets fetched and stored", "count": len(pets)})
    except Exception as e:
        logger.exception("Failed to fetch and store pets")
        return jsonify({"error": "Failed to fetch pets"}), 500


@app.route("/pets", methods=["GET"])
async def get_pets():
    pets = await cache.get_pets()
    return jsonify(pets)


@app.route("/pets/details", methods=["POST"])
async def post_pet_details():
    data = await request.get_json(force=True)
    if not data or "petId" not in data:
        return jsonify({"error": "Missing petId in request body"}), 400
    pet_id = data["petId"]
    try:
        pet_detail = await fetch_pet_detail_from_petstore(pet_id)
        if not pet_detail:
            return jsonify({"error": "Pet not found"}), 404
        await cache.store_pet_detail(pet_detail)
        return jsonify({"message": "Pet details fetched and stored", "petId": pet_id})
    except Exception:
        return jsonify({"error": "Failed to fetch pet details"}), 500


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet_detail(pet_id: int):
    pet = await cache.get_pet_detail(pet_id)
    if not pet:
        return jsonify({"error": "Pet details not found"}), 404
    return jsonify(pet)


@app.route("/pets/favorite", methods=["POST"])
async def post_pet_favorite():
    data = await request.get_json(force=True)
    if not data or "petId" not in data:
        return jsonify({"error": "Missing petId in request body"}), 400
    pet_id = data["petId"]
    pets = await cache.get_pets()
    if not any(p["id"] == pet_id for p in pets):
        return jsonify({"error": "Pet not found in stored pets"}), 404
    await cache.add_favorite(pet_id)
    return jsonify({"message": "Pet marked as favorite", "petId": pet_id})


@app.route("/pets/favorites", methods=["GET"])
async def get_pets_favorites():
    favorites = await cache.get_favorites()
    return jsonify(favorites)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
