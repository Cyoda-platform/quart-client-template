from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

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

# In-memory "cache" and adoption registry (only for async jobs and adoptions, cache replaced by entity_service)
adoptions: Dict[int, Dict[str, Any]] = {}

# Simulated entity jobs for async processing
entity_jobs: Dict[str, Dict[str, Any]] = {}

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

@dataclass
class PetSearchRequest:
    type: str = None
    status: str = None
    limit: int = 10

@dataclass
class PetAdoptRequest:
    petId: int
    adopterName: str
    adopterContact: str

# Helper to fetch pets from external API with filters
async def fetch_pets_from_external(type_: str = None, status: str = None, limit: int = 10):
    query_params = {}
    if status:
        query_params["status"] = status
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            pets = response.json()
        except Exception as e:
            logger.exception(e)
            return []

    if type_:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == type_.lower()]

    return pets[:limit]

async def process_pet_search(job_id: str, data: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_external(
            type_=data.get("type"),
            status=data.get("status"),
            limit=data.get("limit", 10),
        )
        # Save each pet to entity_service asynchronously
        for pet in pets:
            entity_data = {
                "id": pet["id"],
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "description": pet.get("tags")[0]["name"] if pet.get("tags") else "",
            }
            # We cannot await in a for loop without slowing things down much, so just fire and forget
            asyncio.create_task(entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=entity_data,
                technical_id=pet["id"],
                meta={}
            ))
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = pets
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def pets_search(data: PetSearchRequest):
    job_id = f"search-{datetime.utcnow().isoformat()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_pet_search(job_id, data.__dict__))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route("/pets/search/result/<job_id>", methods=["GET"])
async def pets_search_result(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    if job["status"] == "processing":
        return jsonify({"status": "processing"}), 202
    if job["status"] == "failed":
        return jsonify({"status": "failed", "error": job.get("error")}), 500
    results = [
        {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("type"),
            "status": pet.get("status"),
            "description": pet.get("description"),
        }
        for pet in job.get("result", [])
    ]
    return jsonify({"results": results})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(PetAdoptRequest)
async def pets_adopt(data: PetAdoptRequest):
    pet_id = data.petId
    adopter_name = data.adopterName
    adopter_contact = data.adopterContact

    try:
        pet_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Pet not found"}), 404

    if not pet_entity:
        # fallback: fetch from external API
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                r.raise_for_status()
                pet_data = r.json()
                pet_entity = {
                    "id": pet_data.get("id"),
                    "name": pet_data.get("name"),
                    "type": pet_data.get("category", {}).get("name"),
                    "status": pet_data.get("status"),
                    "description": pet_data.get("tags")[0]["name"] if pet_data.get("tags") else "",
                }
                # Add to entity_service for future use
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_entity,
                )
            except Exception as e:
                logger.exception(e)
                return jsonify({"success": False, "message": "Pet not found"}), 404

    adoptions[pet_id] = {
        "pet": pet_entity,
        "adopterName": adopter_name,
        "adopterContact": adopter_contact,
        "adoptedAt": datetime.utcnow().isoformat(),
    }

    # Update pet status to adopted in entity_service
    pet_entity["status"] = "adopted"
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_entity,
            technical_id=pet_id,
            meta={},
        )
    except Exception as e:
        logger.exception(e)

    return jsonify({"success": True, "message": "Adoption request registered"})

@app.route("/pets", methods=["GET"])
async def pets_list():
    try:
        pets_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        pets_entities = []

    pets_list = []
    for pet in pets_entities:
        pets_list.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("type"),
                "status": pet.get("status"),
            }
        )
    return jsonify({"pets": pets_list})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
    except Exception as e:
        logger.exception(e)
        pet = None

    if not pet:
        # fallback: fetch from external API and add to entity_service
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                r.raise_for_status()
                pet_data = r.json()
                pet = {
                    "id": pet_data.get("id"),
                    "name": pet_data.get("name"),
                    "type": pet_data.get("category", {}).get("name"),
                    "status": pet_data.get("status"),
                    "description": pet_data.get("tags")[0]["name"] if pet_data.get("tags") else "",
                }
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet,
                )
            except Exception as e:
                logger.exception(e)
                return jsonify({"error": "Pet not found"}), 404

    adoption_status = "adopted" if pet_id in adoptions else pet.get("status", "unknown")
    pet_detail = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("type"),
        "status": pet.get("status"),
        "description": pet.get("description"),
        "adoptionStatus": adoption_status,
    }
    return jsonify(pet_detail)

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)