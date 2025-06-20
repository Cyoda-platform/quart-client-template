```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "persistence" for adopted pets and last fetched pets cache
# Use asyncio.Lock to avoid race issues
class AppState:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.adopted_pet_ids: set[int] = set()
        self.cached_pets: Dict[int, Dict[str, Any]] = {}

    async def mark_adopted(self, pet_id: int):
        async with self._lock:
            self.adopted_pet_ids.add(pet_id)

    async def is_adopted(self, pet_id: int) -> bool:
        async with self._lock:
            return pet_id in self.adopted_pet_ids

    async def cache_pets(self, pets: List[Dict[str, Any]]):
        async with self._lock:
            for pet in pets:
                self.cached_pets[pet["id"]] = pet

    async def get_cached_pets(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return list(self.cached_pets.values())

    async def get_cached_pet(self, pet_id: int) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self.cached_pets.get(pet_id)


app_state = AppState()

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

# Helper to transform Petstore pet data to app pet data with adoption info
async def transform_pet(pet: Dict[str, Any]) -> Dict[str, Any]:
    pet_id = pet.get("id")
    adopted = await app_state.is_adopted(pet_id) if pet_id is not None else False
    return {
        "id": pet_id,
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "adopted": adopted,
        "photoUrls": pet.get("photoUrls", []),
        # Optional fun description placeholder
        "description": f"{pet.get('name')} is a lovely {pet.get('category', {}).get('name') if pet.get('category') else 'pet'}.",
    }


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Body (JSON): {type?, status?, name?}
    Calls Petstore API /pet/findByStatus or /pet/findByTags or /pet/findByStatus+name filtering
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")
    name_filter = data.get("name")

    # Petstore API supports searching by status via /pet/findByStatus (array of status)
    # It does not support search by type or name directly - we will fetch by status and filter locally.
    # If no status provided, default to "available" per Petstore docs.

    query_statuses = [status] if status else ["available"]

    async with httpx.AsyncClient(timeout=10) as client:
        all_pets = []
        for st in query_statuses:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": st})
                r.raise_for_status()
                pets_data = r.json()
                # pets_data is a list of pets
                all_pets.extend(pets_data)
            except Exception as e:
                logger.exception(f"Error fetching pets by status={st}: {e}")
                # Continue fetching others if exists

    # Filter by type (category.name) if provided
    if pet_type:
        pet_type_lower = pet_type.lower()
        all_pets = [pet for pet in all_pets if pet.get("category", {}).get("name", "").lower() == pet_type_lower]

    # Filter by name partial match if provided
    if name_filter:
        name_filter_lower = name_filter.lower()
        all_pets = [pet for pet in all_pets if pet.get("name") and name_filter_lower in pet["name"].lower()]

    # Transform pets to app format including adopted status
    transformed_pets = []
    for pet in all_pets:
        transformed = await transform_pet(pet)
        transformed_pets.append(transformed)

    # Cache pets internally for GET retrieval
    await app_state.cache_pets(transformed_pets)

    return jsonify({"results": transformed_pets})


@app.route("/pets/adopt", methods=["POST"])
async def pets_adopt():
    """
    POST /pets/adopt
    Body: {petId: integer}
    Simulate adoption by marking pet as adopted internally.
    """
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        abort(400, "petId must be an integer")

    # Check if pet exists in cache
    cached_pet = await app_state.get_cached_pet(pet_id)
    if cached_pet is None:
        # TODO: Could fetch pet from Petstore API, but for prototype, just error out
        abort(404, f"Pet with id {pet_id} not found in app cache. Please search first.")

    await app_state.mark_adopted(pet_id)

    return jsonify({
        "adopted": True,
        "petId": pet_id,
        "message": f"Congratulations! You have adopted {cached_pet.get('name')}."
    })


@app.route("/pets", methods=["GET"])
async def pets_list():
    """
    GET /pets
    Returns the current list of cached pets with adoption info.
    """
    pets = await app_state.get_cached_pets()
    return jsonify({"pets": pets})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    """
    GET /pets/{id}
    Returns detailed info of a specific pet from cache.
    """
    pet = await app_state.get_cached_pet(pet_id)
    if pet is None:
        abort(404, f"Pet with id {pet_id} not found in app cache. Please search first.")

    return jsonify(pet)


if __name__ == '__main__':
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
