from dataclasses import dataclass
import asyncio
import logging
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

# Data models for request validation
@dataclass
class FetchRequest:
    status: Optional[str]
    type: Optional[str]
    limit: int

@dataclass
class CustomizeMessage:
    pet_id: str  # id should be string now
    message_template: str

# In-memory cache for job statuses only; pets_data replaced by entity_service
entity_jobs: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str], limit: int) -> List[Dict]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status or "available,pending,sold"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise
    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    return pets[:limit]

def enrich_pet_description(pet: Dict) -> str:
    name = pet.get("name", "Unnamed")
    pet_type = pet.get("category", {}).get("name", "pet").lower()
    status = pet.get("status", "unknown")
    description = f"{name} is a lovely {pet_type} currently {status}."
    if pet_type == "cat":
        description += " Loves naps and chasing yarn balls! 😸"
    elif pet_type == "dog":
        description += " Always ready for a walk and lots of belly rubs! 🐶"
    else:
        description += " A wonderful companion waiting for you!"
    return description

async def process_entity(entity_job: Dict, params: Dict):
    try:
        pets = await fetch_pets_from_petstore(params.get("status"), params.get("type"), params.get("limit", 10))
        enriched = []
        for pet in pets:
            enriched.append({
                "id": str(pet.get("id")),  # ensure id is string
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", "").lower(),
                "status": pet.get("status"),
                "description": enrich_pet_description(pet),
            })
        # Store pets in entity_service
        # Delete old pets first (assuming pet ids are unique strings)
        existing_pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        for existing_pet in existing_pets:
            try:
                await entity_service.delete_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    technical_id=existing_pet.get("id"),
                    meta={},
                )
            except Exception as e:
                logger.warning(f"Failed to delete existing pet id {existing_pet.get('id')}: {e}")
        # Add new pets
        for pet in enriched:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet,
                )
            except Exception as e:
                logger.warning(f"Failed to add pet id {pet.get('id')}: {e}")
        entity_job.update({
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "count": len(enriched),
        })
        logger.info(f"Processed {len(enriched)} pets")
    except Exception as e:
        entity_job["status"] = "failed"
        entity_job["error"] = str(e)
        logger.exception("Error in processing entity job")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchRequest)  # workaround: validate_request must be last in POST due to quart-schema issue
async def fetch_pets(data: FetchRequest):
    job_id = f"job-{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_entity(entity_jobs[job_id], data.__dict__))
    return jsonify({"message": "Pets data fetch started", "job_id": job_id}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get pets from entity_service")
        return jsonify({"error": "Failed to retrieve pets"}), 500
    return jsonify(pets)

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": f"Pet with id {pet_id} not found"}), 404
    except Exception as e:
        logger.exception(f"Failed to get pet id {pet_id} from entity_service")
        return jsonify({"error": "Failed to retrieve pet"}), 500
    return jsonify(pet)

@app.route("/pets/customize-message", methods=["POST"])
@validate_request(CustomizeMessage)  # workaround: validate_request must be last in POST due to quart-schema issue
async def customize_message(data: CustomizeMessage):
    pet_id = data.pet_id
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": f"Pet with id {pet_id} not found"}), 404
    except Exception as e:
        logger.exception(f"Failed to get pet id {pet_id} from entity_service")
        return jsonify({"error": "Failed to retrieve pet"}), 500
    try:
        updated = data.message_template.format(name=pet.get("name"))
    except Exception:
        return jsonify({"error": "Invalid message_template format"}), 400
    pet["description"] = updated
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={},
        )
    except Exception as e:
        logger.exception(f"Failed to update pet id {pet_id}")
        return jsonify({"error": "Failed to update pet description"}), 500
    return jsonify({"pet_id": pet_id, "updated_description": updated})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)