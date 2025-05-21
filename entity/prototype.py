import asyncio
import logging
import uuid
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# In-memory local caches for search and detail results
search_results = {}
detail_results = {}

def gen_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets_from_petstore(type_: str = None, status: str = None):
    params = {}
    if status:
        params["status"] = status
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pets from Petstore: {e}")
            return []

async def fetch_pet_details_from_petstore(pet_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet details from Petstore: {e}")
            return None

async def process_search_job(job_id: str, type_: str, status: str):
    logger.info(f"Processing search job {job_id} with type={type_} status={status}")
    pets = await fetch_pets_from_petstore(type_, status)
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
        "description": pet.get("description") or ""
    }
    detail_results[detail_id]["status"] = "completed"
    detail_results[detail_id]["pet"] = normalized
    detail_results[detail_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Detail job {detail_id} completed for petId={pet_id}")

@dataclass
class SearchRequest:
    type: str = None
    status: str = None

@dataclass
class DetailRequest:
    petId: int

@app.route("/pets/search", methods=["POST"])
# workaround: quart-schema bug requires validate_request last for POST
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    job_id = gen_id()
    search_results[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "pets": []
    }
    asyncio.create_task(process_search_job(job_id, data.type, data.status))
    return jsonify({"searchId": job_id, "message": "Search started"}), 202

@app.route("/pets/results/<string:search_id>", methods=["GET"])
async def pets_results(search_id):
    job = search_results.get(search_id)
    if not job:
        return jsonify({"error": "searchId not found"}), 404
    if job["status"] != "completed":
        return jsonify({"searchId": search_id, "status": job["status"], "message": "Results not ready"}), 202
    return jsonify({"searchId": search_id, "pets": job["pets"]})

@app.route("/pets/details", methods=["POST"])
# workaround: quart-schema bug requires validate_request last for POST
@validate_request(DetailRequest)
async def pets_details(data: DetailRequest):
    pet_id = data.petId
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
    return jsonify({"detailId": detail_id, "pet": job["pet"]})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)