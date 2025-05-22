from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # validate_querystring available if needed

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class SearchRequest:
    type: str = None
    status: str = None
    name: str = None

@dataclass
class DetailsRequest:
    petId: int

# In-memory async-safe caches
search_cache = {}
details_cache = {}
search_cache_lock = asyncio.Lock()
details_cache_lock = asyncio.Lock()

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

def generate_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets(filters: dict) -> list:
    status = filters.get("status")
    type_filter = filters.get("type")
    name_filter = filters.get("name")
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching pets: {e}")
        return []
    def matches(p):
        if type_filter and p.get("category", {}).get("name", "").lower() != type_filter.lower():
            return False
        if name_filter and name_filter.lower() not in p.get("name", "").lower():
            return False
        return True
    filtered = [p for p in pets if matches(p)]
    result = []
    for p in filtered:
        result.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        })
    return result

async def fetch_pet_details(pet_id: int) -> dict:
    url = f"{PETSTORE_BASE}/pet/{pet_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            p = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching details: {e}")
        return {}
    detail = {
        "id": p.get("id"),
        "name": p.get("name"),
        "type": p.get("category", {}).get("name"),
        "status": p.get("status"),
        "photoUrls": p.get("photoUrls", []),
        "description": "No description available.",  # TODO: enrich from other source
        "tags": [t.get("name") for t in p.get("tags", [])] if p.get("tags") else [],
    }
    return detail

async def process_search_job(search_id: str, filters: dict):
    logger.info(f"Processing search job {search_id}")
    pets = await fetch_pets(filters)
    async with search_cache_lock:
        search_cache[search_id]["status"] = "done"
        search_cache[search_id]["pets"] = pets
        search_cache[search_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Search job {search_id} done")

async def process_details_job(pet_id: int):
    logger.info(f"Processing details job for {pet_id}")
    details = await fetch_pet_details(pet_id)
    async with details_cache_lock:
        details_cache[pet_id] = {
            "status": "done",
            "details": details,
            "completedAt": datetime.utcnow().isoformat(),
        }
    logger.info(f"Details job for {pet_id} done")

@app.route("/pets/search", methods=["POST"])
# workaround: validate_request must go last for POST methods due to quart-schema defect
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    search_id = generate_id()
    now = datetime.utcnow().isoformat()
    async with search_cache_lock:
        search_cache[search_id] = {"status": "processing", "requestedAt": now, "pets": []}
    asyncio.create_task(process_search_job(search_id, data.__dict__))
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
# workaround: validate_request must go last for POST methods due to quart-schema defect
@validate_request(DetailsRequest)
async def pets_details(data: DetailsRequest):
    pet_id = data.petId
    async with details_cache_lock:
        if pet_id in details_cache:
            if details_cache[pet_id]["status"] == "processing":
                return jsonify({"status": "processing"}), 202
            if details_cache[pet_id]["status"] == "done":
                return jsonify(details_cache[pet_id]["details"])
        details_cache[pet_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "details": None}
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
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)