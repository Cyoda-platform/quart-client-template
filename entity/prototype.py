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

# In-memory async-safe "cache" (simple dict wrapped with asyncio.Lock)
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets: Dict[int, Dict] = {}       # petId -> pet data
        self._adoptions: Dict[str, List[int]] = {}  # adopter email -> list of petIds

    async def set_pets(self, pets: List[Dict]):
        async with self._lock:
            for pet in pets:
                self._pets[pet["id"]] = pet

    async def get_pet(self, pet_id: int) -> Optional[Dict]:
        async with self._lock:
            return self._pets.get(pet_id)

    async def search_pets(
        self,
        name: Optional[str] = None,
        status: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> List[Dict]:
        async with self._lock:
            results = list(self._pets.values())
        if name:
            results = [p for p in results if name.lower() in p.get("name", "").lower()]
        if status:
            results = [p for p in results if p.get("status") in status]
        if category:
            results = [p for p in results if p.get("category", {}).get("name", "").lower() == category.lower()]
        return results

    async def add_adoption(self, adopter_email: str, pet_id: int):
        async with self._lock:
            self._adoptions.setdefault(adopter_email, [])
            if pet_id not in self._adoptions[adopter_email]:
                self._adoptions[adopter_email].append(pet_id)

    async def get_adoptions(self, adopter_email: str) -> List[int]:
        async with self._lock:
            return self._adoptions.get(adopter_email, [])

cache = AsyncCache()

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Helper to convert Petstore pet data to app pet data with fun tags
def transform_petstore_pet(pet: Dict) -> Dict:
    pet_id = pet.get("id")
    name = pet.get("name", "")
    category = pet.get("category") or {}
    status = pet.get("status", "available")
    tags = [tag.get("name") for tag in pet.get("tags", []) if "name" in tag]

    # Add playful tag based on category
    if category.get("name", "").lower() == "cat":
        tags.append("purrfect")
    elif category.get("name", "").lower() == "dog":
        tags.append("woof-tastic")
    else:
        tags.append("pet-tastic")

    return {
        "id": pet_id,
        "name": name,
        "category": category,
        "status": status,
        "tags": tags,
    }

@app.route("/pets/sync", methods=["POST"])
async def pets_sync():
    """
    POST /pets/sync
    Body: {"filter": {"status": "available"}}
    Fetch pets from Petstore API and cache them.
    """
    data = await request.get_json(force=True)
    status_filter = None
    try:
        status_filter = data.get("filter", {}).get("status")
    except Exception:
        pass

    params = {}
    if status_filter:
        params["status"] = status_filter

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            r.raise_for_status()
            pets_raw = r.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to fetch pets from external API"}), 502

    pets_transformed = [transform_petstore_pet(p) for p in pets_raw]
    await cache.set_pets(pets_transformed)

    return jsonify({
        "syncedCount": len(pets_transformed),
        "message": "Pets data synced successfully."
    })

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Body: {name?, status?, category?}
    Search cached pets.
    """
    data = await request.get_json(force=True)
    name = data.get("name")
    status = data.get("status")  # Expected list or None
    if isinstance(status, str):
        status = [status]
    category = data.get("category")

    results = await cache.search_pets(name=name, status=status, category=category)
    return jsonify({"results": results})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get(pet_id: int):
    """
    GET /pets/{petId}
    Return cached pet details.
    """
    pet = await cache.get_pet(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/adopt", methods=["POST"])
async def pets_adopt():
    """
    POST /pets/adopt
    Body: {petId, adopter: {name, email}}
    Process adoption request.
    """
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    adopter = data.get("adopter", {})
    adopter_name = adopter.get("name")
    adopter_email = adopter.get("email")

    if not pet_id or not adopter_name or not adopter_email:
        return jsonify({"error": "Missing petId or adopter information"}), 400

    pet = await cache.get_pet(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    # TODO: Add business logic validations (e.g. check pet availability)
    if pet.get("status") != "available":
        return jsonify({"success": False, "message": f"Sorry, {pet['name']} is not available for adoption."}), 400

    # Mark pet as adopted (update cached status)
    pet["status"] = "adopted"
    await cache.set_pets([pet])

    # Record adoption
    await cache.add_adoption(adopter_email, pet_id)

    return jsonify({
        "success": True,
        "message": f"Congrats {adopter_name}! You adopted {pet['name']}."
    })

@app.route("/adoptions/<string:adopter_email>", methods=["GET"])
async def get_adoptions(adopter_email: str):
    """
    GET /adoptions/{adopterEmail}
    Return list of adopted pets for the adopter.
    """
    pet_ids = await cache.get_adoptions(adopter_email)
    pets = []
    for pid in pet_ids:
        pet = await cache.get_pet(pid)
        if pet:
            pets.append({
                "id": pet["id"],
                "name": pet["name"],
                "category": pet.get("category", {})
            })

    return jsonify({
        "adopter": adopter_email,
        "adoptedPets": pets
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
