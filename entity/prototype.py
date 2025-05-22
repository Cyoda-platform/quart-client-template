import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class MatchmakeRequest:
    preferredType: Optional[str] = None
    preferredStatus: Optional[str] = None

pets_cache: Dict[int, dict] = {}
entity_jobs: Dict[str, dict] = {}
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[dict]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
    except Exception as e:
        logger.exception("Error fetching pets from Petstore API")
        return []

async def calculate_match_score(pet: dict, preferred_type: Optional[str], preferred_status: Optional[str]) -> float:
    score = 0.0
    if preferred_type and pet.get("category", {}).get("name", "").lower() == preferred_type.lower():
        score += 0.6
    if preferred_status and pet.get("status", "").lower() == preferred_status.lower():
        score += 0.4
    return score

async def process_fetch_pets_job(job_id: str, pet_type: Optional[str], status: Optional[str]):
    entity_jobs[job_id]["status"] = "processing"
    try:
        pets = await fetch_pets_from_petstore(pet_type, status)
        for pet in pets:
            pets_cache[pet["id"]] = pet
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"count": len(pets)}
        logger.info(f"Fetched and cached {len(pets)} pets for job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception("Failed to process fetch pets job")

async def process_matchmake_job(job_id: str, preferred_type: Optional[str], preferred_status: Optional[str]):
    entity_jobs[job_id]["status"] = "processing"
    try:
        pets = await fetch_pets_from_petstore(preferred_type, preferred_status)
        matched_pets = []
        for pet in pets:
            score = await calculate_match_score(pet, preferred_type, preferred_status)
            if score > 0:
                p = pet.copy()
                p["matchScore"] = round(score, 2)
                matched_pets.append(p)
        for pet in pets:
            pets_cache[pet["id"]] = pet
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"matchedPets": matched_pets}
        logger.info(f"Matchmaking completed with {len(matched_pets)} matches for job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception("Failed to process matchmaking job")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # Workaround: place validation last for POST due to validate_request defect
async def pets_fetch(data: FetchPetsRequest):
    pet_type = data.type
    status = data.status
    job_id = f"fetch-{datetime.utcnow().isoformat()}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_pets_job(job_id, pet_type, status))
    return jsonify({"jobId": job_id, "status": "started"}), 202

@app.route("/pets/matchmake", methods=["POST"])
@validate_request(MatchmakeRequest)  # Workaround: place validation last for POST due to validate_request defect
async def pets_matchmake(data: MatchmakeRequest):
    preferred_type = data.preferredType
    preferred_status = data.preferredStatus
    job_id = f"matchmake-{datetime.utcnow().isoformat()}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_matchmake_job(job_id, preferred_type, preferred_status))
    return jsonify({"jobId": job_id, "status": "started"}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    return jsonify({"pets": list(pets_cache.values())})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    pet_detail = pet.copy()
    pet_detail["description"] = f"Meet {pet_detail.get('name', 'this pet')}! A lovely {pet_detail.get('category', {}).get('name', 'pet')} waiting for a new home."
    return jsonify(pet_detail)

@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)