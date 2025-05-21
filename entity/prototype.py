```python
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache and favorites store
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets_data: Optional[Dict] = None
        self._favorites: Dict[int, Dict] = {}

    async def set_pets(self, data: Dict):
        async with self._lock:
            self._pets_data = data

    async def get_pets(self) -> Optional[Dict]:
        async with self._lock:
            return self._pets_data

    async def add_favorite(self, pet: Dict):
        async with self._lock:
            self._favorites[pet["id"]] = pet

    async def remove_favorite(self, pet_id: int):
        async with self._lock:
            if pet_id in self._favorites:
                del self._favorites[pet_id]

    async def get_favorites(self) -> List[Dict]:
        async with self._lock:
            return list(self._favorites.values())


cache = AsyncCache()

# Constants
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    category: Optional[str], status: Optional[str], limit: Optional[int]
) -> Dict:
    """
    Fetch pets from the Petstore API applying filters.
    Petstore API supports filtering by status only, category is a tag in their model.
    We'll fetch by status, then filter by category manually.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        # Petstore API endpoint to find pets by status
        # Status can be comma-separated string, e.g. "available,sold"
        status_param = status if status else "available"
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status_param})
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore: {e}")
            # Return empty response to avoid app failure
            pets = []

    # Filter by category (Petstore uses 'category' object with 'name')
    if category:
        filtered = []
        for pet in pets:
            cat = pet.get("category")
            if cat and cat.get("name", "").lower() == category.lower():
                filtered.append(pet)
        pets = filtered

    if limit:
        pets = pets[:limit]

    # Compose response structure
    response = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(pets),
        "pets": pets,
    }
    return response


async def process_fetch_pets(data: Dict):
    """
    Background task to fetch pets and store in cache.
    """
    try:
        category = data.get("category")
        status = data.get("status")
        limit = data.get("limit")
        if isinstance(limit, int) and limit <= 0:
            limit = None  # ignore invalid limits

        pets_data = await fetch_pets_from_petstore(category, status, limit)
        await cache.set_pets(pets_data)
        logger.info(f"Fetched and cached {pets_data['total']} pets (category={category}, status={status})")
    except Exception as e:
        logger.exception(f"Failed processing fetch pets: {e}")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Request JSON:
    {
      "category": "string",        (optional)
      "status": "string",          (optional)
      "limit": 10                  (optional)
    }
    Response: returns fetched pet data.
    """
    data = await request.get_json(force=True, silent=True) or {}
    # Fire and forget background fetching, but respond immediately
    asyncio.create_task(process_fetch_pets(data))
    return jsonify({"message": "Fetch started, pets will be updated shortly."}), 202


@app.route("/pets", methods=["GET"])
async def pets_get():
    """
    GET /pets
    Returns the latest fetched pet data.
    """
    pets_data = await cache.get_pets()
    if not pets_data:
        return jsonify({"message": "No pet data available. Please POST /pets/fetch to load data."}), 404
    return jsonify(pets_data)


@app.route("/pets/favorite", methods=["POST"])
async def pets_favorite():
    """
    POST /pets/favorite
    Request JSON:
    {
      "pet_id": int,
      "favorite": bool
    }
    Response:
    {
      "pet_id": int,
      "favorite": bool,
      "message": str
    }
    """
    data = await request.get_json(force=True, silent=True) or {}
    pet_id = data.get("pet_id")
    favorite = data.get("favorite")

    if not isinstance(pet_id, int) or not isinstance(favorite, bool):
        return jsonify({"message": "Invalid input, 'pet_id' must be int and 'favorite' must be bool."}), 400

    pets_data = await cache.get_pets()
    if not pets_data:
        return jsonify({"message": "No pet data available. Please POST /pets/fetch to load data."}), 404

    # Find pet in stored pets
    pet = next((p for p in pets_data["pets"] if p.get("id") == pet_id), None)
    if not pet:
        return jsonify({"message": f"Pet with id {pet_id} not found."}), 404

    if favorite:
        await cache.add_favorite(pet)
        msg = "Pet marked as favorite"
    else:
        await cache.remove_favorite(pet_id)
        msg = "Pet unmarked as favorite"

    return jsonify({"pet_id": pet_id, "favorite": favorite, "message": msg})


@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    """
    GET /pets/favorites
    Returns the list of favorite pets.
    """
    favorites = await cache.get_favorites()
    return jsonify({"favorites": favorites})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
