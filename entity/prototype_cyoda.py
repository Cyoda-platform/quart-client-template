import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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

# In-memory cache on app.state only for jobs
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
            "id": str(pet.get("id")),
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
        # save pets as items in entity_service, one by one
        # first clear existing pets stored? No instruction, so just add
        # Because add_item returns id, but we already have ids from petstore, we skip usage of add_item here
        # Instead, we'll store all pets with update_item or add_item as needed
        # But the instruction says to replace local cache with entity_service calls, so we store pets with add_item
        # We'll create new pets with add_item, ignoring existing ids because add_item generates new technical ids
        # So pet id from external is lost; we store pet dict as is, with id as string in data

        # We'll store all pets in entity_service, collect their new ids
        stored_ids = []
        for pet in pets:
            pet_data = pet.copy()
            if "id" in pet_data:
                pet_data["id"] = str(pet_data["id"])  # ensure string
            new_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data
            )
            stored_ids.append(new_id)

        app.state.entity_jobs[job_id].update({
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "result_count": len(stored_ids),
            "stored_ids": stored_ids,
        })
        logger.info(f"Fetch job {job_id} completed with {len(stored_ids)} pets stored.")
    except Exception as e:
        logger.exception(e)
        app.state.entity_jobs[job_id].update({"status": "failed", "error": str(e)})

async def process_filter_job(job_id: str, data: dict):
    try:
        # Retrieve all pets from entity_service
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        filtered = await apply_filter_logic(pets, data.get("min_age"), data.get("max_age"), data.get("fun_category"))
        # We cannot store filtered pets in local cache, so store filtered pets as separate entities or skip storing?
        # Instruction does not specify storing filtered pets, so we just keep filtered list in job meta
        # But local cache for pets_filtered removed, so store filtered pets as separate entities is not specified
        # We'll just store filtered pets list in job meta for retrieval

        app.state.entity_jobs[job_id].update({
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "result_count": len(filtered),
            "filtered_pets": filtered,
        })
        logger.info(f"Filter job {job_id} completed with {len(filtered)} pets.")
    except Exception as e:
        logger.exception(e)
        app.state.entity_jobs[job_id].update({"status": "failed", "error": str(e)})

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    job_id = get_next_job_id()
    app.state.entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_job(job_id, data.__dict__))
    return jsonify({"message": f"Fetch job started with id {job_id}", "job_id": job_id}), 202

@app.route("/pets/filter", methods=["POST"])
@validate_request(FilterPetsRequest)
async def pets_filter(data: FilterPetsRequest):
    job_id = get_next_job_id()
    app.state.entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_filter_job(job_id, data.__dict__))
    return jsonify({"message": f"Filter job started with id {job_id}", "job_id": job_id}), 202

@app.route("/pets", methods=["GET"])
async def pets_get():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pet_get(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

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