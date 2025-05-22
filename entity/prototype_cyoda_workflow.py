from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class FetchPetsRequest:
    filters: dict
    sortBy: Optional[str]
    limit: int

@dataclass
class AdoptionRequest:
    pet_id: int
    user_name: str
    user_email: str

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def process_pet(entity: dict) -> dict:
    # Add a processedAt timestamp before persistence
    entity['processedAt'] = datetime.utcnow().isoformat()
    return entity

async def process_pet_fetch_job(entity: dict) -> dict:
    # Workflow for pet_fetch_job entity to fetch pets and add/update pet entities
    filters = entity.get("filters") or {}
    sort_by = entity.get("sortBy")
    limit = entity.get("limit")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        limit = 50

    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            statuses = filters.get("status") or "available,pending,sold"
            params = {"status": statuses}
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            r.raise_for_status()
            all_pets = r.json()

        type_filter = filters.get("type")
        pets = []
        if type_filter:
            type_filter_lower = type_filter.lower()
            for pet in all_pets:
                pet_type = pet.get("category", {}).get("name", "").lower()
                if pet_type == type_filter_lower:
                    pets.append(pet)
                if len(pets) >= limit:
                    break
        else:
            pets = all_pets[:limit]

        if sort_by == "name":
            pets.sort(key=lambda p: p.get("name", "").lower())

        for pet in pets:
            pet_id_str = str(pet["id"])
            pet_data = {
                "id": pet["id"],
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", "unknown"),
                "status": pet.get("status"),
                "age": None,
                "description": pet.get("description", ""),
                "photos": pet.get("photoUrls", []),
            }
            try:
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                    technical_id=pet_id_str,
                    meta={},
                )
            except Exception:
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="pet",
                        entity_version=ENTITY_VERSION,
                        entity=pet_data,
                        workflow=process_pet,
                    )
                except Exception as add_ex:
                    logger.error(f"Failed to add pet id {pet_id_str}: {add_ex}")

        entity["status"] = "completed"
        entity["count"] = len(pets)
        entity["completedAt"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception("Error in process_pet_fetch_job")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()

    return entity

async def process_adoption_request(entity: dict) -> dict:
    pet_id = entity.get("petId")
    if pet_id is None:
        entity["status"] = "failed"
        entity["error"] = "Missing petId"
        logger.error("Adoption request missing petId")
        return entity

    pet_id_str = str(pet_id)
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id_str,
        )
        if not pet:
            raise ValueError(f"Pet with id {pet_id_str} not found")

        entity["status"] = "submitted"
        entity["submittedAt"] = datetime.utcnow().isoformat()

        user = entity.get("user", {})
        user_name = user.get("name")
        user_email = user.get("email")

        logger.info(f"Adoption request submitted for pet {pet_id_str} by {user_name} ({user_email})")

    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.error(f"Failed processing adoption request: {e}")

    return entity

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    job_entity = {
        "filters": data.filters,
        "sortBy": data.sortBy,
        "limit": data.limit if 0 < data.limit <= 100 else 50,
        "createdAt": datetime.utcnow().isoformat(),
        "status": "pending",
    }

    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=process_pet_fetch_job,
        )
    except Exception as e:
        logger.error(f"Failed to create pet_fetch_job: {e}")
        return jsonify({"error": "Failed to create pet fetch job"}), 500

    return jsonify({
        "message": "Pets fetch job created",
        "jobId": job_id,
        "status": "pending"
    })

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        pets_list = []
        for pet in items:
            pets_list.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("type"),
                "status": pet.get("status"),
                "age": pet.get("age"),
            })
        return jsonify(pets_list)
    except Exception:
        logger.exception("Failed to retrieve pets")
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet_details(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception:
        logger.exception(f"Failed to retrieve pet with id {pet_id}")
        return jsonify({"error": "Pet not found"}), 404

@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionRequest)
async def create_adoption(data: AdoptionRequest):
    adoption_entity = {
        "petId": data.pet_id,
        "user": {
            "name": data.user_name,
            "email": data.user_email
        },
        "createdAt": datetime.utcnow().isoformat(),
        "status": "pending"
    }

    try:
        request_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoption_request",
            entity_version=ENTITY_VERSION,
            entity=adoption_entity,
            workflow=process_adoption_request,
        )
    except Exception as e:
        logger.error(f"Failed to create adoption request: {e}")
        return jsonify({"error": "Failed to create adoption request"}), 500

    return jsonify({
        "message": "Adoption request created",
        "requestId": request_id,
        "status": "pending"
    })

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)