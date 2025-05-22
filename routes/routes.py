import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
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

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class MatchmakeRequest:
    preferredType: Optional[str] = None
    preferredStatus: Optional[str] = None

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> list:
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
    except Exception:
        logger.exception("Error fetching pets from Petstore API")
        return []

async def calculate_match_score(pet: dict, preferred_type: Optional[str], preferred_status: Optional[str]) -> float:
    score = 0.0
    if preferred_type and pet.get("category", {}).get("name", "").lower() == preferred_type.lower():
        score += 0.6
    if preferred_status and pet.get("status", "").lower() == preferred_status.lower():
        score += 0.4
    return score

async def process_pet(entity: dict) -> None:
    # Add a processedAt timestamp
    entity['processedAt'] = datetime.utcnow().isoformat()
    # Add a description if missing or empty
    if "description" not in entity or not entity["description"]:
        name = entity.get("name", "this pet")
        category = entity.get("category", {}).get("name", "pet")
        entity["description"] = f"Meet {name}! A lovely {category} waiting for a new home."

async def process_pet_fetch_job(entity: dict) -> None:
    # This workflow runs when a pet_fetch_job entity is created
    pet_type = entity.get("type")
    status = entity.get("status")
    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()
    try:
        pets = await fetch_pets_from_petstore(pet_type, status)
        for pet_data in pets:
            # Add pet entities with process_pet workflow
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data
                )
            except Exception:
                logger.exception("Failed to add pet entity in pet_fetch_job workflow")
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result"] = {"count": len(pets)}
    except Exception as e:
        logger.exception("Failed processing pet_fetch_job")
        entity["status"] = "failed"
        entity["error"] = str(e)

async def process_pet_matchmake_job(entity: dict) -> None:
    preferred_type = entity.get("preferredType")
    preferred_status = entity.get("preferredStatus")
    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()
    try:
        pets = await fetch_pets_from_petstore(preferred_type, preferred_status)
        matched_pets = []
        for pet in pets:
            score = await calculate_match_score(pet, preferred_type, preferred_status)
            if score > 0:
                p = pet.copy()
                p["matchScore"] = round(score, 2)
                matched_pets.append(p)
            # Add pet entities anyway with process_pet workflow
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet
                )
            except Exception:
                logger.exception("Failed to add pet entity in pet_matchmake_job workflow")
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result"] = {"matchedPets": matched_pets}
    except Exception as e:
        logger.exception("Failed processing pet_matchmake_job")
        entity["status"] = "failed"
        entity["error"] = str(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    job_id = f"fetch-{datetime.utcnow().isoformat()}"
    job_entity = {
        "jobId": job_id,
        "type": data.type,
        "status": "queued",
        "statusRequestedAt": datetime.utcnow().isoformat(),
        "statusRequestedBy": "api"
    }
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_fetch_job",
        entity_version=ENTITY_VERSION,
        entity=job_entity
    )
    return jsonify({"jobId": job_id, "status": "started"}), 202

@app.route("/pets/matchmake", methods=["POST"])
@validate_request(MatchmakeRequest)
async def pets_matchmake(data: MatchmakeRequest):
    job_id = f"matchmake-{datetime.utcnow().isoformat()}"
    job_entity = {
        "jobId": job_id,
        "preferredType": data.preferredType,
        "preferredStatus": data.preferredStatus,
        "status": "queued",
        "statusRequestedAt": datetime.utcnow().isoformat(),
        "statusRequestedBy": "api"
    }
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_matchmake_job",
        entity_version=ENTITY_VERSION,
        entity=job_entity
    )
    return jsonify({"jobId": job_id, "status": "started"}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"pets": pets})
    except Exception:
        logger.exception("Failed to retrieve pets list")
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
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
    except Exception:
        logger.exception(f"Failed to retrieve pet id={pet_id}")
        return jsonify({"error": "Pet not found"}), 404

@app.route("/jobs/<string:job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    job = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="pet_fetch_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_matchmake_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)