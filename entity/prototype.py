import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None
    limit: Optional[int] = None

@dataclass
class FilterPetsRequest:
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    fun_category: Optional[str] = None

# In-memory cache on app.state
app.state.pets_fetched: List[Dict] = []
app.state.pets_filtered: List[Dict] = []
app.state.entity_jobs: Dict[str, Dict] = {}

# External API base
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

_job_counter = 0
def get_next_job_id() -> str:
    global _job_counter
    _job_counter += 1
    return str(_job_counter)

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str], limit: Optional[int]) -> List[Dict]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception(f"Failed to fetch pets: {e}")
        pets = []
    if pet_type:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
    if limit:
        pets = pets[:limit]
    normalized = []
    import random
    for pet in pets:
        normalized.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else "unknown",
            "age": random.randint(1, 10),  # TODO: real age calculation if available
            "status": pet.get("status"),
            "fun_category": None,
        })
    return normalized

async def apply_filter_logic(pets: List[Dict], min_age: Optional[int], max_age: Optional[int], fun_category: Optional[str]) -> List[Dict]:
    filtered = []
    for pet in pets:
        age = pet.get("age")
        if min_age is not None and (age is None or age < min_age):
            continue
        if max_age is not None and (age is None or age > max_age):
            continue
        p = pet.copy()
        if fun_category:
            p["fun_category"] = fun_category
        else:
            if age is not None:
                if age <= 3:
                    p["fun_category"] = "playful"
                elif age >= 7:
                    p["fun_category"] = "sleepy"
                else:
                    p["fun_category"] = "neutral"
            else:
                p["fun_category"] = "unknown"
        filtered.append(p)
    return filtered

async def process_fetch_job(job_id: str, data: dict):
    try:
        pets = await fetch_pets_from_petstore(data.get("type"), data.get("status"), data.get("limit"))
        app.state.pets_fetched = pets
        app.state.pets_filtered = pets
        app.state.entity_jobs[job_id].update({
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "result_count": len(pets),
        })
        logger.info(f"Fetch job {job_id} completed with {len(pets)} pets.")
    except Exception as e:
        logger.exception(e)
        app.state.entity_jobs[job_id].update({"status": "failed", "error": str(e)})

async def process_filter_job(job_id: str, data: dict):
    try:
        filtered = await apply_filter_logic(app.state.pets_fetched, data.get("min_age"), data.get("max_age"), data.get("fun_category"))
        app.state.pets_filtered = filtered
        app.state.entity_jobs[job_id].update({
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "result_count": len(filtered),
        })
        logger.info(f"Filter job {job_id} completed with {len(filtered)} pets.")
    except Exception as e:
        logger.exception(e)
        app.state.entity_jobs[job_id].update({"status": "failed", "error": str(e)})

@app.route("/pets/fetch", methods=["POST"])
# Validation last for POST due to quart-schema defect workaround
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    job_id = get_next_job_id()
    app.state.entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_job(job_id, data.__dict__))
    return jsonify({"message": f"Fetch job started with id {job_id}", "job_id": job_id}), 202

@app.route("/pets/filter", methods=["POST"])
# Validation last for POST due to quart-schema defect workaround
@validate_request(FilterPetsRequest)
async def pets_filter(data: FilterPetsRequest):
    job_id = get_next_job_id()
    app.state.entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_filter_job(job_id, data.__dict__))
    return jsonify({"message": f"Filter job started with id {job_id}", "job_id": job_id}), 202

@app.route("/pets", methods=["GET"])
async def pets_get():
    return jsonify(app.state.pets_filtered)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_get(pet_id: int):
    pet = next((p for p in app.state.pets_filtered if p["id"] == pet_id), None)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/jobs/<job_id>", methods=["GET"])
async def job_status(job_id: str):
    job = app.state.entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)