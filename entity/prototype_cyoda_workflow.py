from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

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
class PetQuery:
    action: str
    data: dict

entity_jobs: Dict[str, Dict[str, Any]] = {}

# Helper function to fetch available pets from external petstore asynchronously
async def fetch_available_pets_from_petstore() -> List[Dict[str, Any]]:
    url = "https://petstore.swagger.io/v2/pet/findByStatus?status=available"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=10)
        r.raise_for_status()
        return r.json()

# Workflow function for pet entity, applied before persistence
async def process_pet(entity: Dict[str, Any]) -> None:
    # Add processed timestamp to entity
    entity['processed_at'] = datetime.utcnow().isoformat()

    # Normalize pet name to title case if present
    if 'name' in entity and isinstance(entity['name'], str):
        entity['name'] = entity['name'].title()

    # Enrich category with description if category id present
    category = entity.get('category')
    if category and isinstance(category, dict) and 'id' in category:
        category['description'] = f"Category {category['id']} description (enriched)"

    # Transform tags to uppercase strings if present
    if 'tags' in entity and isinstance(entity['tags'], list):
        entity['tags'] = [tag.upper() if isinstance(tag, str) else tag for tag in entity['tags']]

    # Example placeholder for adding related entities of different model if needed (commented out)
    # await entity_service.add_item(
    #     token=cyoda_auth_service,
    #     entity_model="pet_metadata",
    #     entity_version=ENTITY_VERSION,
    #     entity={"pet_id": entity.get("id"), "meta": "some meta info"},
    #     workflow=None
    # )

# Entity job processor for async tasks triggered by endpoints
async def process_entity_job(job_id: str, data: Dict[str, Any]):
    try:
        action = data.get("action")
        payload = data.get("data", {})

        if action == "fetch_all":
            pets = await fetch_available_pets_from_petstore()
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = pets

        elif action == "fetch_by_type":
            pet_type = payload.get("type")
            if not pet_type:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = "Missing 'type' in data"
                return
            pets = await fetch_available_pets_from_petstore()
            filtered = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = filtered

        elif action == "add_pet":
            pet_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=payload,
                workflow=process_pet
            )
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = {"id": pet_id}

        elif action == "update_pet":
            pet_id = str(payload.get("id"))
            if not pet_id:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = "Missing 'id' in data"
                return

            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            if not existing:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = f"Pet id {pet_id} not found"
                return

            # Check if update_item supports workflow, otherwise remove workflow param
            # Assuming support here:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=payload,
                technical_id=pet_id,
                meta={},
                workflow=process_pet
            )

            updated = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = updated

        elif action == "delete_pet":
            pet_id = str(payload.get("id"))
            if not pet_id:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = "Missing 'id' in data"
                return
            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            if not existing:
                entity_jobs[job_id]["status"] = "error"
                entity_jobs[job_id]["result"] = f"Pet id {pet_id} not found"
                return
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
                meta={}
            )
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = existing

        else:
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["result"] = f"Unsupported action: {action}"

    except Exception as e:
        logger.exception("Error processing entity job")
        entity_jobs[job_id]["status"] = "error"
        entity_jobs[job_id]["result"] = str(e)

@app.route("/pets/query", methods=["POST"])
@validate_request(PetQuery)
async def pets_query(data: PetQuery):
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "result": None,
    }
    asyncio.create_task(process_entity_job(job_id, data.__dict__))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route("/pets", methods=["GET"])
async def list_pets():
    pets = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model="pet",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(pets)

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    pet = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="pet",
        entity_version=ENTITY_VERSION,
        technical_id=str(pet_id)
    )
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/job_status/<job_id>", methods=["GET"])
async def get_job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)