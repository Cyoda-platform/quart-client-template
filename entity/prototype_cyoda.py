import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from app_init.app_init import BeanFactory

from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# Data classes for request validation
@dataclass
class PetSearchRequest:
    type: Optional[str]
    status: Optional[str]
    tags: Optional[List[str]]

@dataclass
class AdoptionRequest:
    pet_id: str  # changed to string as per instruction
    adopter_name: str
    contact_info: str

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(criteria: Dict[str, Any]) -> Any:
    async with httpx.AsyncClient() as client:
        status = criteria.get("status", "available")
        tags = criteria.get("tags", [])
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

    pet_type = criteria.get("type")
    filtered = []
    for pet in pets:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            continue
        if tags:
            pet_tags = {tag["name"].lower() for tag in pet.get("tags", [])}
            if not all(t.lower() in pet_tags for t in tags):
                continue
        filtered.append(pet)

    return filtered

async def process_pet_search_job(search_id: str, criteria: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_petstore(criteria)
        data = {
            "status": "completed",
            "pets": pets,
            "count": len(pets),
            "completedAt": datetime.utcnow().isoformat()
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pets_search",
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=search_id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Error processing pet search job {search_id}: {e}")
        data = {
            "status": "failed",
            "error": str(e)
        }
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pets_search",
                entity_version=ENTITY_VERSION,
                entity=data,
                technical_id=search_id,
                meta={}
            )
        except Exception as e2:
            logger.exception(f"Failed to update error state for pet search job {search_id}: {e2}")

async def process_adoption_workflow(adoption_id: str, adoption_data: Dict[str, Any]):
    try:
        steps = [
            "application_received",
            "background_check",
            "adoption_approved",
            "pet_delivered",
            "completed",
        ]
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="adoptions",
            entity_version=ENTITY_VERSION,
            entity={"status": "processing", "steps_completed": []},
            technical_id=adoption_id,
            meta={}
        )

        for step in steps:
            await asyncio.sleep(1)
            # get current state
            current_data = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="adoptions",
                entity_version=ENTITY_VERSION,
                technical_id=adoption_id
            )
            steps_completed = current_data.get("steps_completed", [])
            steps_completed.append(step)
            status = "completed" if step == "completed" else step
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="adoptions",
                entity_version=ENTITY_VERSION,
                entity={"steps_completed": steps_completed, "status": status},
                technical_id=adoption_id,
                meta={}
            )

    except Exception as e:
        logger.exception(f"Error in adoption workflow {adoption_id}: {e}")
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="adoptions",
                entity_version=ENTITY_VERSION,
                entity={"status": "failed", "error": str(e)},
                technical_id=adoption_id,
                meta={}
            )
        except Exception as e2:
            logger.exception(f"Failed to update error state for adoption workflow {adoption_id}: {e2}")

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)  # Workaround: validate_request after @app.route due to quart-schema defect
async def pets_search(data: PetSearchRequest):
    criteria = data.__dict__
    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    search_entry = {
        "status": "processing",
        "requestedAt": requested_at,
        "criteria": criteria,
        "pets": [],
        "count": 0,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pets_search",
            entity_version=ENTITY_VERSION,
            entity=search_entry
        )
    except Exception as e:
        logger.exception(f"Error adding pets_search item: {e}")
        return jsonify({"error": "Failed to initiate search"}), 500

    # The add_item call returns an id, but we already generated one as search_id,
    # so we must keep consistent. Because we cannot set the id explicitly in add_item,
    # fallback: store the search_entry with generated id via update_item after add_item?
    # But per instruction, skip if not enough functions; so we keep our id and use update_item to store it.

    # Actually, to store with custom id, we need to use update_item not add_item.
    # So instead of add_item, use update_item with technical_id=search_id
    try:
        # Overwrite with correct id
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pets_search",
            entity_version=ENTITY_VERSION,
            entity=search_entry,
            technical_id=search_id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Error updating pets_search item with id {search_id}: {e}")
        return jsonify({"error": "Failed to initiate search"}), 500

    asyncio.create_task(process_pet_search_job(search_id, criteria))

    return jsonify({"search_id": search_id, "count": 0}), 202

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_pets_search_results(search_id):
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pets_search",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception(f"Error fetching pets_search item with id {search_id}: {e}")
        return jsonify({"error": "Search ID not found"}), 404

    if not entry:
        return jsonify({"error": "Search ID not found"}), 404

    if entry.get("status") == "processing":
        return jsonify({"status": "processing"}), 202

    pets_resp = []
    for p in entry.get("pets", []):
        pets_resp.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", [])] if p.get("tags") else [],
            }
        )
    return jsonify({"search_id": search_id, "pets": pets_resp})

@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionRequest)  # Workaround: validate_request after @app.route due to quart-schema defect
async def create_adoption(data: AdoptionRequest):
    adoption_id = str(uuid.uuid4())
    adoption_entry = {
        "status": "initiated",
        "requestedAt": datetime.utcnow().isoformat(),
        "pet_id": data.pet_id,
        "adopter_name": data.adopter_name,
        "contact_info": data.contact_info,
        "steps_completed": [],
    }
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="adoptions",
            entity_version=ENTITY_VERSION,
            entity=adoption_entry,
            technical_id=adoption_id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Error creating adoption item with id {adoption_id}: {e}")
        return jsonify({"error": "Failed to create adoption"}), 500

    asyncio.create_task(process_adoption_workflow(adoption_id, data.__dict__))

    return jsonify({"adoption_id": adoption_id, "status": "initiated"}), 202

@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption_status(adoption_id):
    try:
        adoption = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="adoptions",
            entity_version=ENTITY_VERSION,
            technical_id=adoption_id
        )
    except Exception as e:
        logger.exception(f"Error fetching adoption item with id {adoption_id}: {e}")
        return jsonify({"error": "Adoption ID not found"}), 404

    if not adoption:
        return jsonify({"error": "Adoption ID not found"}), 404

    return jsonify(
        {
            "adoption_id": adoption_id,
            "pet_id": adoption.get("pet_id"),
            "adopter_name": adoption.get("adopter_name"),
            "status": adoption.get("status"),
            "steps_completed": adoption.get("steps_completed", []),
        }
    )

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)