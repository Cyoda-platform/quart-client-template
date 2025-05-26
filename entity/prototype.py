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

# In-memory caches (async-safe usage via asyncio.Lock)
search_results = {}
favorites = {}
search_lock = asyncio.Lock()
favorites_lock = asyncio.Lock()

# External Petstore API base URL (public Swagger Petstore)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper async function to fetch pets from Petstore API with filters
async def fetch_pets_from_petstore(filters: dict):
    """
    Fetch pets from Petstore API using the /pet/findByStatus endpoint as a proxy.
    Petstore API doesn't support complex filtering (type/breed/age), so we simulate filtering here.
    TODO: Replace with a real API that supports filtering or extend with local filtering logic.
    """
    status = "available"  # Only fetch available pets
    async with httpx.AsyncClient() as client:
        try:
            # Petstore API: GET /pet/findByStatus?status=available
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed to fetch pets from external Petstore API")
            return []

    # Simulate filtering locally (Petstore API lacks breed/age filtering)
    filtered = []
    for pet in pets:
        # pet['category'] might be None or dict with 'name' (e.g. "dog", "cat")
        pet_type = pet.get("category", {}).get("name", "").lower()
        if filters.get("type") and filters["type"].lower() != pet_type:
            continue
        # Breed is not available in Petstore API - skipping breed filter
        # Age is not available - skipping age filter
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
async def pets_search():
    data = await request.get_json(force=True)
    # Accept keys: type (string), breed (string), ageRange {min,max} - breed and ageRange ignored by Petstore API
    filters = {
        "type": data.get("type"),
        "breed": data.get("breed"),  # not used, placeholder
        "ageRange": data.get("ageRange"),  # not used, placeholder
    }
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    async with search_lock:
        search_results[job_id] = {"status": "processing", "requestedAt": requested_at, "pets": None}
    # Fire and forget processing task
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
        # status == completed
        return jsonify({"resultsId": results_id, "pets": job["pets"]})

@app.route("/pets/favorite", methods=["POST"])
async def pets_favorite():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not pet_id:
        return jsonify({"success": False, "message": "petId is required"}), 400
    async with favorites_lock:
        favorites[pet_id] = True
    return jsonify({"success": True, "message": "Pet added to favorites."})

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    async with favorites_lock:
        fav_ids = list(favorites.keys())

    # TODO: For a real app, we would fetch pet details from DB or cache.
    # Here, we mock favorite pet details by returning minimal info with petId.
    # This is a placeholder until a persistence layer is added.
    pets = [{"id": pid, "name": f"Pet {pid}", "type": "unknown", "breed": "unknown", "age": -1, "imageUrl": ""} for pid in fav_ids]

    return jsonify({"favorites": pets})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
