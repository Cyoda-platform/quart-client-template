import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# DATA CLASSES FOR REQUESTS

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

# EXTERNAL API UTILS

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

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
        return []
    if pet_type:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
    if limit:
        pets = pets[:limit]
    import random
    normalized = []
    for pet in pets:
        normalized.append({
            "id": str(pet.get("id")),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else "unknown",
            "age": random.randint(1, 10),  # Simulated age
            "status": pet.get("status"),
            "fun_category": None,
        })
    return normalized

# FILTER LOGIC

def apply_filter_logic_sync(pets: List[Dict], min_age: Optional[int], max_age: Optional[int], fun_category: Optional[str]) -> List[Dict]:
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

# WORKFLOW FUNCTIONS

async def process_pet(entity: dict):
    # Add a processedAt timestamp before persistence.
    entity["processedAt"] = datetime.utcnow().isoformat()

async def process_pet_fetch_job(entity: dict):
    # Guard against multiple runs if already completed or failed
    if entity.get("status") in ("completed", "failed"):
        return

    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    # Defensive: petstore api params must not be None type
    pet_type = entity.get("type")
    status_filter = entity.get("status_filter")
    limit = entity.get("limit")
    try:
        pets = await fetch_pets_from_petstore(
            pet_type=pet_type,
            status=status_filter,
            limit=limit
        )
        stored_ids = []
        for pet in pets:
            pet_data = pet.copy()
            if "id" in pet_data:
                pet_data["id"] = str(pet_data["id"])
            # Add pet entity with workflow
            new_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data,
                workflow=process_pet
            )
            stored_ids.append(new_id)

        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result_count"] = len(stored_ids)
        entity["stored_ids"] = stored_ids

    except Exception as e:
        logger.exception("Error in pet_fetch_job workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()

async def process_pet_filter_job(entity: dict):
    if entity.get("status") in ("completed", "failed"):
        return

    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        filtered = apply_filter_logic_sync(
            pets,
            min_age=entity.get("min_age"),
            max_age=entity.get("max_age"),
            fun_category=entity.get("fun_category")
        )
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result_count"] = len(filtered)
        entity["filtered_pets"] = filtered

    except Exception as e:
        logger.exception("Error in pet_filter_job workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()

# ENDPOINTS

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    job_entity = {
        "type": data.type,
        "status_filter": data.status,
        "limit": data.limit,
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    job_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_fetch_job",
        entity_version=ENTITY_VERSION,
        entity=job_entity,
        workflow=process_pet_fetch_job
    )
    return jsonify({"message": "Fetch job started", "job_id": job_id}), 202

@app.route("/pets/filter", methods=["POST"])
@validate_request(FilterPetsRequest)
async def pets_filter(data: FilterPetsRequest):
    job_entity = {
        "min_age": data.min_age,
        "max_age": data.max_age,
        "fun_category": data.fun_category,
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    job_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_filter_job",
        entity_version=ENTITY_VERSION,
        entity=job_entity,
        workflow=process_pet_filter_job
    )
    return jsonify({"message": "Filter job started", "job_id": job_id}), 202

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

@app.route("/jobs/<string:job_id>", methods=["GET"])
async def job_status(job_id: str):
    job = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="pet_fetch_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_filter_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)

# MAIN

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)