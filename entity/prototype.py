from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SearchRequest:
    type: str = None
    status: str = None

@dataclass
class DetailRequest:
    petId: int

# In-memory cache for search and detail results
app.state.search_cache = {}
app.state.detail_cache = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

def generate_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets_from_petstore(type_: str = None, status: str = None) -> list:
    query_params = {}
    if status:
        query_params["status"] = status
    if not status:
        query_params["status"] = "available"
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=query_params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            if type_:
                return [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore: {e}")
            return []

async def fetch_pet_detail_from_petstore(pet_id: int) -> dict:
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Failed fetching pet detail for id {pet_id}: {e}")
            return {}

async def process_search(search_id: str, type_: str, status: str):
    app.state.search_cache[search_id]["status"] = "processing"
    try:
        pets = await fetch_pets_from_petstore(type_, status)
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

async def process_detail(detail_id: str, pet_id: int):
    app.state.detail_cache[detail_id]["status"] = "processing"
    try:
        pet = await fetch_pet_detail_from_petstore(pet_id)
        description = pet.get("description") or "No description available."  # TODO: placeholder
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

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)  # issue workaround: validation last for POST
async def pets_search(data: SearchRequest):
    search_id = generate_id()
    app.state.search_cache[search_id] = {
        "status": "pending",
        "requestedAt": datetime.utcnow(),
        "results": None,
    }
    asyncio.create_task(process_search(search_id, data.type, data.status))
    return jsonify({"searchId": search_id})

@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    cache = app.state.search_cache.get(search_id)
    if not cache:
        return jsonify({"error": "searchId not found"}), 404
    if cache["status"] != "done":
        return jsonify({"searchId": search_id, "status": cache["status"], "results": None})
    return jsonify({"searchId": search_id, "results": cache["results"]})

@app.route("/pets/details", methods=["POST"])
@validate_request(DetailRequest)  # issue workaround: validation last for POST
async def pets_details(data: DetailRequest):
    detail_id = generate_id()
    app.state.detail_cache[detail_id] = {
        "status": "pending",
        "requestedAt": datetime.utcnow(),
        "detail": None,
    }
    asyncio.create_task(process_detail(detail_id, data.petId))
    return jsonify({"detailId": detail_id})

@app.route("/pets/details/<string:detail_id>", methods=["GET"])
async def get_pet_detail(detail_id):
    cache = app.state.detail_cache.get(detail_id)
    if not cache:
        return jsonify({"error": "detailId not found"}), 404
    if cache["status"] != "done":
        return jsonify({"detailId": detail_id, "status": cache["status"], "detail": None})
    return jsonify({"detailId": detail_id, **cache["detail"]})

if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)