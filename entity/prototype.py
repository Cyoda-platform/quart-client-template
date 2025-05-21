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

# In-memory local caches for search and detail results
search_results = {}
detail_results = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility function to generate IDs
def gen_id() -> str:
    return str(uuid.uuid4())


async def fetch_pets_from_petstore(type_: str = None, status: str = None):
    """Call Petstore API to find pets by status and type."""
    params = {}
    # Petstore API supports status filtering only by "status"
    # type filtering is not directly supported by Petstore API; we'll filter client-side.
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            # Filter by type client side if provided
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pets from Petstore: {e}")
            return []


async def fetch_pet_details_from_petstore(pet_id: int):
    """Call Petstore API to get pet details by petId"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            response.raise_for_status()
            pet = response.json()
            return pet
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet details from Petstore: {e}")
            return None


async def process_search_job(job_id: str, type_: str, status: str):
    logger.info(f"Processing search job {job_id} with type={type_} status={status}")
    pets = await fetch_pets_from_petstore(type_, status)
    # Normalize pets to minimal fields for response
    normalized = []
    for p in pets:
        normalized.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", [])
        })
    search_results[job_id]["status"] = "completed"
    search_results[job_id]["pets"] = normalized
    search_results[job_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Search job {job_id} completed with {len(normalized)} pets")


async def process_detail_job(detail_id: str, pet_id: int):
    logger.info(f"Processing detail job {detail_id} for petId={pet_id}")
    pet = await fetch_pet_details_from_petstore(pet_id)
    if pet is None:
        detail_results[detail_id]["status"] = "failed"
        detail_results[detail_id]["pet"] = None
        detail_results[detail_id]["completedAt"] = datetime.utcnow().isoformat()
        return

    normalized = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "description": pet.get("description") or ""  # Petstore API does not have description, so empty string
    }
    detail_results[detail_id]["status"] = "completed"
    detail_results[detail_id]["pet"] = normalized
    detail_results[detail_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Detail job {detail_id} completed for petId={pet_id}")


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")
    job_id = gen_id()
    search_results[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "pets": []
    }
    # Fire and forget processing
    asyncio.create_task(process_search_job(job_id, type_, status))
    return jsonify({"searchId": job_id, "message": "Search started"}), 202


@app.route("/pets/results/<string:search_id>", methods=["GET"])
async def pets_results(search_id):
    job = search_results.get(search_id)
    if not job:
        return jsonify({"error": "searchId not found"}), 404
    if job["status"] != "completed":
        return jsonify({"searchId": search_id, "status": job["status"], "message": "Results not ready"}), 202
    return jsonify({
        "searchId": search_id,
        "pets": job["pets"]
    })


@app.route("/pets/details", methods=["POST"])
async def pets_details():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400
    detail_id = gen_id()
    detail_results[detail_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "pet": None
    }
    asyncio.create_task(process_detail_job(detail_id, pet_id))
    return jsonify({"detailId": detail_id, "message": "Detail fetch started"}), 202


@app.route("/pets/details/<string:detail_id>", methods=["GET"])
async def pets_details_result(detail_id):
    job = detail_results.get(detail_id)
    if not job:
        return jsonify({"error": "detailId not found"}), 404
    if job["status"] != "completed":
        return jsonify({"detailId": detail_id, "status": job["status"], "message": "Detail not ready"}), 202
    return jsonify({
        "detailId": detail_id,
        "pet": job["pet"]
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
