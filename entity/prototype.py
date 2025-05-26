from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches (async-safe usage via asyncio.Lock)
search_results = {}
favorites = {}
search_lock = asyncio.Lock()
favorites_lock = asyncio.Lock()

# External Petstore API base URL (public Swagger Petstore)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

@dataclass
class SearchRequest:
    type: str = None
    breed: str = None
    ageRange: dict = None  # TODO: nested dict validation not supported, placeholder

@dataclass
class FavoriteRequest:
    petId: str

# Helper async function to fetch pets from Petstore API with filters
async def fetch_pets_from_petstore(filters: dict):
    status = "available"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed to fetch pets from external Petstore API")
            return []

    filtered = []
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower()
        if filters.get("type") and filters["type"].lower() != pet_type:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type,
            "breed": "unknown",  # TODO: Breed info missing in Petstore API
            "age": -1,           # TODO: Age info missing in Petstore API
            "description": pet.get("status", ""),
            "imageUrl": pet.get("photoUrls")[0] if pet.get("photoUrls") else "",
        })
    return filtered

async def process_search(job_id: str, filters: dict):
    try:
        pets = await fetch_pets_from_petstore(filters)
        async with search_lock:
            search_results[job_id]["status"] = "completed"
            search_results[job_id]["pets"] = pets
    except Exception as e:
        logger.exception(f"Error processing search job {job_id}")
        async with search_lock:
            search_results[job_id]["status"] = "failed"
            search_results[job_id]["error"] = str(e)

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)  # Workaround: place validation last for POST due to quart-schema defect
async def pets_search(data: SearchRequest):
    filters = {
        "type": data.type,
        "breed": data.breed,
        "ageRange": data.ageRange,
    }
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    async with search_lock:
        search_results[job_id] = {"status": "processing", "requestedAt": requested_at, "pets": None}
    asyncio.create_task(process_search(job_id, filters))
    return jsonify({"resultsId": job_id})

@app.route("/pets/results/<results_id>", methods=["GET"])
async def pets_results(results_id):
    async with search_lock:
        job = search_results.get(results_id)
        if not job:
            return jsonify({"error": "resultsId not found"}), 404
        if job["status"] == "processing":
            return jsonify({"resultsId": results_id, "status": "processing", "pets": None})
        if job["status"] == "failed":
            return jsonify({"resultsId": results_id, "status": "failed", "error": job.get("error")}), 500
        return jsonify({"resultsId": results_id, "pets": job["pets"]})

@app.route("/pets/favorite", methods=["POST"])
@validate_request(FavoriteRequest)  # Workaround: place validation last for POST due to quart-schema defect
async def pets_favorite(data: FavoriteRequest):
    pet_id = data.petId
    async with favorites_lock:
        favorites[pet_id] = True
    return jsonify({"success": True, "message": "Pet added to favorites."})

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    async with favorites_lock:
        fav_ids = list(favorites.keys())
    pets = [{"id": pid, "name": f"Pet {pid}", "type": "unknown", "breed": "unknown", "age": -1, "imageUrl": ""} for pid in fav_ids]
    return jsonify({"favorites": pets})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)