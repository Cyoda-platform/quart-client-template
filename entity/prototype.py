```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache placeholders
# Structure: search_results: dict[str, list[dict]]
# Structure: adoptions: dict[str, list[dict]]
class AsyncCache:
    def __init__(self):
        self._search_results = {}
        self._adoptions = {}
        self._lock = asyncio.Lock()

    async def save_search(self, search_id: str, pets: list[dict]):
        async with self._lock:
            self._search_results[search_id] = pets

    async def get_search(self, search_id: str):
        async with self._lock:
            return self._search_results.get(search_id)

    async def add_adoption(self, adopter_name: str, pet: dict):
        async with self._lock:
            if adopter_name not in self._adoptions:
                self._adoptions[adopter_name] = []
            self._adoptions[adopter_name].append(pet)

    async def get_adoptions(self, adopter_name: str):
        async with self._lock:
            return self._adoptions.get(adopter_name, [])


cache = AsyncCache()

# Real Petstore API base URL
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Helper function to query pets with criteria from Petstore API
async def query_pets(type_: str = None, status: str = None, tags: list[str] = None) -> list[dict]:
    params = {}
    if status:
        params["status"] = status
    # Petstore API does not support type or tags filtering directly via query params,
    # so we fetch by status and filter manually.
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from external API: {e}")
            return []

    # Filter by type and tags locally since Petstore API does not support those filters
    def pet_matches(pet: dict) -> bool:
        if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
            return False
        if tags:
            pet_tags = [t.get("name", "").lower() for t in pet.get("tags", [])]
            if not all(t.lower() in pet_tags for t in tags):
                return False
        return True

    filtered = [p for p in pets if pet_matches(p)]
    return filtered


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Request JSON:
    {
        "type": "cat" (optional),
        "status": "available" (optional),
        "tags": ["cute", "small"] (optional)
    }
    Response JSON:
    {
        "searchId": "string"
    }
    """
    data = await request.get_json()
    type_ = data.get("type")
    status = data.get("status")
    tags = data.get("tags")

    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Received pet search request {search_id} with filters type={type_}, status={status}, tags={tags}")

    async def process_search(search_id, type_, status, tags):
        pets = await query_pets(type_, status, tags)
        # Map pets to simplified structure for the app
        simplified_pets = []
        for p in pets:
            simplified_pets.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")]
            })
        await cache.save_search(search_id, simplified_pets)
        logger.info(f"Processed pet search {search_id} with {len(simplified_pets)} results")

    # Fire and forget search processing
    asyncio.create_task(process_search(search_id, type_, status, tags))

    return jsonify({"searchId": search_id})


@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    """
    GET /pets/search/{searchId}
    Response JSON:
    {
        "searchId": "string",
        "pets": [ {pet}, ...]
    }
    """
    pets = await cache.get_search(search_id)
    if pets is None:
        return jsonify({"error": "Search ID not found or results not ready"}), 404
    return jsonify({"searchId": search_id, "pets": pets})


@app.route("/pets/adopt", methods=["POST"])
async def adopt_pet():
    """
    POST /pets/adopt
    Request JSON:
    {
        "petId": integer,
        "adopterName": "string"
    }
    Response JSON:
    {
        "petId": integer,
        "adopterName": "string",
        "adoptionStatus": "confirmed"
    }
    """
    data = await request.get_json()
    pet_id = data.get("petId")
    adopter_name = data.get("adopterName")

    if not pet_id or not adopter_name:
        return jsonify({"error": "petId and adopterName are required"}), 400

    # TODO: In a real app, verify pet exists and is adoptable.
    # Here we mock adoption by storing petId and adopterName.

    # We'll try to find pet info from cached searches for better UX.
    pet_info = None
    # Aggregate pets from all searches to find the pet info (inefficient but OK for prototype)
    for search_id in list(cache._search_results.keys()):
        pets = await cache.get_search(search_id)
        if pets:
            for pet in pets:
                if pet["id"] == pet_id:
                    pet_info = pet
                    break
        if pet_info:
            break

    if pet_info is None:
        # Fallback: minimal info if not found in cache
        pet_info = {"id": pet_id, "name": None, "type": None, "status": None}

    await cache.add_adoption(adopter_name, pet_info)
    logger.info(f"Pet {pet_id} adopted by {adopter_name}")

    return jsonify({
        "petId": pet_id,
        "adopterName": adopter_name,
        "adoptionStatus": "confirmed"
    })


@app.route("/pets/adoptions/<adopter_name>", methods=["GET"])
async def get_adoptions(adopter_name):
    """
    GET /pets/adoptions/{adopterName}
    Response JSON:
    {
        "adopterName": "string",
        "adoptedPets": [ {pet}, ...]
    }
    """
    adopted_pets = await cache.get_adoptions(adopter_name)
    return jsonify({
        "adopterName": adopter_name,
        "adoptedPets": adopted_pets
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
