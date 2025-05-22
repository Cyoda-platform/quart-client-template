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

# In-memory async-safe caches
# Using asyncio.Lock to avoid race conditions
search_cache = {}
details_cache = {}
search_cache_lock = asyncio.Lock()
details_cache_lock = asyncio.Lock()

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

# Helper function to generate unique IDs
def generate_id() -> str:
    return str(uuid.uuid4())


async def fetch_pets(filters: dict) -> list:
    """Fetch pets from Petstore API applying filters."""
    # Petstore API /pet/findByStatus supports status filter only
    # We will do filtering client side for type, name (since Petstore API is limited)

    status = filters.get("status")
    type_filter = filters.get("type")
    name_filter = filters.get("name")

    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    else:
        # Default to available pets if no status
        params["status"] = "available"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching pets from Petstore API: {e}")
        # Return empty list on error (could be improved with retry or fallback)
        return []

    # Filter by type and name client-side
    def matches(p):
        if type_filter and p.get("category", {}).get("name", "").lower() != type_filter.lower():
            return False
        if name_filter and name_filter.lower() not in p.get("name", "").lower():
            return False
        return True

    filtered = [p for p in pets if matches(p)]

    # Map to simplified output format
    result = []
    for p in filtered:
        result.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "photoUrls": p.get("photoUrls", []),
            }
        )
    return result


async def fetch_pet_details(pet_id: int) -> dict:
    """Fetch detailed pet info from Petstore API by petId."""
    url = f"{PETSTORE_BASE}/pet/{pet_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            p = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching pet details from Petstore API: {e}")
        return {}

    # Map to expected detailed output format
    detail = {
        "id": p.get("id"),
        "name": p.get("name"),
        "type": p.get("category", {}).get("name"),
        "status": p.get("status"),
        "photoUrls": p.get("photoUrls", []),
        # Petstore API does not have description or tags explicitly; we mock
        "description": "No description available.",  # TODO: Could enrich or fetch from other source
        "tags": [t.get("name") for t in p.get("tags", [])] if p.get("tags") else [],
    }
    return detail


async def process_search_job(search_id: str, filters: dict):
    logger.info(f"Started processing search job {search_id} with filters {filters}")
    pets = await fetch_pets(filters)
    async with search_cache_lock:
        search_cache[search_id]["status"] = "done"
        search_cache[search_id]["pets"] = pets
        search_cache[search_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Completed search job {search_id} with {len(pets)} results")


async def process_details_job(pet_id: int):
    logger.info(f"Started processing details job for petId {pet_id}")
    details = await fetch_pet_details(pet_id)
    async with details_cache_lock:
        details_cache[pet_id] = {
            "status": "done",
            "details": details,
            "completedAt": datetime.utcnow().isoformat(),
        }
    logger.info(f"Completed details job for petId {pet_id}")


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request data"}), 400

    search_id = generate_id()
    now = datetime.utcnow().isoformat()

    async with search_cache_lock:
        search_cache[search_id] = {
            "status": "processing",
            "requestedAt": now,
            "pets": [],
        }

    # Fire and forget the processing task
    asyncio.create_task(process_search_job(search_id, data))

    return jsonify({"searchId": search_id})


@app.route("/pets/search/<search_id>", methods=["GET"])
async def pets_search_results(search_id):
    async with search_cache_lock:
        job = search_cache.get(search_id)
        if not job:
            return jsonify({"error": "Search ID not found"}), 404
        if job["status"] != "done":
            return jsonify({"status": job["status"]}), 202

        return jsonify({"pets": job["pets"]})


@app.route("/pets/details", methods=["POST"])
async def pets_details():
    data = await request.get_json()
    if not isinstance(data, dict) or "petId" not in data:
        return jsonify({"error": "Invalid request data, petId required"}), 400

    pet_id = data["petId"]
    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400

    async with details_cache_lock:
        if pet_id in details_cache and details_cache[pet_id]["status"] == "processing":
            # Already processing
            return jsonify({"status": "processing"}), 202
        elif pet_id in details_cache and details_cache[pet_id]["status"] == "done":
            # Return cached details immediately
            return jsonify(details_cache[pet_id]["details"])

        # Mark as processing
        details_cache[pet_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "details": None,
        }

    # Fire and forget the processing task
    asyncio.create_task(process_details_job(pet_id))

    return jsonify({"status": "processing"}), 202


@app.route("/pets/details/<int:pet_id>", methods=["GET"])
async def pets_details_get(pet_id):
    async with details_cache_lock:
        job = details_cache.get(pet_id)
        if not job:
            return jsonify({"error": "Pet details not found"}), 404
        if job["status"] != "done":
            return jsonify({"status": job["status"]}), 202

        return jsonify(job["details"])


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
