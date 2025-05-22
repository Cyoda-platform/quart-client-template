import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request models
@dataclass
class PetFetchRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class PetMatchRequest:
    preferredType: Optional[str] = None
    preferredStatus: Optional[str] = None

# In-memory cache for pets data keyed by "latest"
pets_cache: Dict[str, List[Dict]] = {}
entity_jobs: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> List[Dict]:
    statuses = [status] if status else ["available", "pending", "sold"]
    pets: List[Dict] = []
    async with httpx.AsyncClient() as client:
        for s in statuses:
            try:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": s})
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
                else:
                    logger.warning(f"Unexpected format: {data}")
            except Exception as e:
                logger.exception(e)
    if type_:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]
    return pets

async def process_fetch_pets_job(job_id: str, filters: Dict):
    try:
        pets = await fetch_pets_from_petstore(filters.get("type"), filters.get("status"))
        pets_cache["latest"] = pets
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"pets": pets}
        logger.info(f"Fetch job {job_id} completed with {len(pets)} pets.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["result"] = {"error": str(e)}
        logger.exception(e)

async def process_pet_match_job(job_id: str, preferences: Dict):
    try:
        pets = pets_cache.get("latest", [])
        filtered = pets
        pt = preferences.get("preferredType", "").lower()
        ps = preferences.get("preferredStatus", "").lower()
        if pt:
            filtered = [p for p in filtered if p.get("category", {}).get("name", "").lower() == pt]
        if ps:
            filtered = [p for p in filtered if p.get("status", "").lower() == ps]
        matched_pet = filtered[0] if filtered else None
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"matchedPet": matched_pet}
        logger.info(f"Match job {job_id} completed. Matched: {matched_pet}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["result"] = {"error": str(e)}
        logger.exception(e)

def create_job() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)  # validation last due to Quart-Schema POST defect workaround
async def pets_fetch(data: PetFetchRequest):
    filters = data.__dict__
    job_id = create_job()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_pets_job(job_id, filters))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets", methods=["GET"])
async def get_cached_pets():
    pets = pets_cache.get("latest", [])
    return jsonify({"pets": pets})

@app.route("/pets/match", methods=["POST"])
@validate_request(PetMatchRequest)  # validation last due to Quart-Schema POST defect workaround
async def pet_match(data: PetMatchRequest):
    preferences = data.__dict__
    job_id = create_job()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_pet_match_job(job_id, preferences))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)