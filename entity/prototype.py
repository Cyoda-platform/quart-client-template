```python
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for search and detail results: {id: data}
# Stored as dict for demo only, no global keyword used (all inside app.state)
# Structure:
# app.state.search_cache: {searchId: {"status": str, "requestedAt": datetime, "results": [...]}}
# app.state.detail_cache: {detailId: {"status": str, "requestedAt": datetime, "detail": {...}}}

app.state.search_cache = {}
app.state.detail_cache = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility to generate unique IDs
def generate_id() -> str:
    return str(uuid.uuid4())

# Async function to fetch pets by criteria from Petstore API
async def fetch_pets_from_petstore(type_: str = None, status: str = None) -> list:
    query_params = {}
    if status:
        query_params["status"] = status
    # Petstore "findByStatus" endpoint exists, but no direct type filter, so we filter after fetch.
    # If no status given, default to available (to limit data)
    if not status:
        query_params["status"] = "available"

    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=query_params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            # Filter by type if provided
            if type_:
                filtered = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]
                return filtered
            return pets
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore: {e}")
            return []

# Async function to fetch pet detail from Petstore API
async def fetch_pet_detail_from_petstore(pet_id: int) -> dict:
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            pet = response.json()
            return pet
        except Exception as e:
            logger.exception(f"Failed fetching pet detail for id {pet_id}: {e}")
            return {}

# Background task to process search request and cache results
async def process_search(search_id: str, type_: str, status: str):
    app.state.search_cache[search_id]["status"] = "processing"
    try:
        pets = await fetch_pets_from_petstore(type_, status)
        # Store results with minimal fields as per API spec
        results = []
        for pet in pets:
            results.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name") if pet.get("category") else None,
                "status": pet.get("status")
            })
        app.state.search_cache[search_id]["results"] = results
        app.state.search_cache[search_id]["status"] = "done"
    except Exception as e:
        logger.exception(f"Error processing search {search_id}: {e}")
        app.state.search_cache[search_id]["status"] = "error"

# Background task to process pet detail request and cache result
async def process_detail(detail_id: str, pet_id: int):
    app.state.detail_cache[detail_id]["status"] = "processing"
    try:
        pet = await fetch_pet_detail_from_petstore(pet_id)
        # Process pet detail: add "description" placeholder if missing
        description = pet.get("description")
        if not description:
            # TODO: Petstore API does not provide description, so we add a placeholder
            description = "No description available."
        pet_processed = {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "description": description,
        }
        app.state.detail_cache[detail_id]["detail"] = pet_processed
        app.state.detail_cache[detail_id]["status"] = "done"
    except Exception as e:
        logger.exception(f"Error processing detail {detail_id}: {e}")
        app.state.detail_cache[detail_id]["status"] = "error"

# POST /pets/search
@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")

    search_id = generate_id()
    requested_at = datetime.utcnow()
    app.state.search_cache[search_id] = {
        "status": "pending",
        "requestedAt": requested_at,
        "results": None,
    }

    # Fire-and-forget processing
    asyncio.create_task(process_search(search_id, type_, status))

    return jsonify({"searchId": search_id})

# GET /pets/search/{searchId}
@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    cache = app.state.search_cache.get(search_id)
    if not cache:
        return jsonify({"error": "searchId not found"}), 404
    if cache["status"] != "done":
        return jsonify({"searchId": search_id, "status": cache["status"], "results": None})
    return jsonify({"searchId": search_id, "results": cache["results"]})

# POST /pets/details
@app.route("/pets/details", methods=["POST"])
async def pets_details():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400

    detail_id = generate_id()
    requested_at = datetime.utcnow()
    app.state.detail_cache[detail_id] = {
        "status": "pending",
        "requestedAt": requested_at,
        "detail": None,
    }

    asyncio.create_task(process_detail(detail_id, pet_id))

    return jsonify({"detailId": detail_id})

# GET /pets/details/{detailId}
@app.route("/pets/details/<string:detail_id>", methods=["GET"])
async def get_pet_detail(detail_id):
    cache = app.state.detail_cache.get(detail_id)
    if not cache:
        return jsonify({"error": "detailId not found"}), 404
    if cache["status"] != "done":
        return jsonify({"detailId": detail_id, "status": cache["status"], "detail": None})
    return jsonify({"detailId": detail_id, **cache["detail"]})

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
