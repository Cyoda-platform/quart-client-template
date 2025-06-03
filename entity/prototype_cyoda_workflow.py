from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = None
cyoda_auth_service = None

# Initialize services
try:
    from app_init.app_init import BeanFactory
    factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
    entity_service = factory.get_services()['entity_service']
    cyoda_auth_service = factory.get_services()["cyoda_auth_service"]
except Exception as e:
    logger.exception(e)

@dataclass
class SearchParams:
    type: str
    status: str
    tags: List[str] = None

@dataclass
class AddPet:
    name: str
    type: str
    status: str
    tags: List[str]
    description: str

@dataclass
class UpdatePet:
    id: str  # id now string per instructions
    name: str
    status: str

@dataclass
class DeletePet:
    id: str  # id now string

entity_jobs: Dict[str, Dict[str, Any]] = {}
entity_jobs_lock = asyncio.Lock()

PET_ENTITY_NAME = "pet"  # entity name lowercase underscore form 'pet'

async def process_search(entity_job: Dict[str, Any], params: Dict[str, Any]):
    try:
        condition = {
            "type": "group",
            "operator": "AND",
            "conditions": []
        }
        if params.get("status") is not None:
            condition["conditions"].append({
                "jsonPath": "$.status",
                "operatorType": "EQUALS",
                "value": params["status"],
                "type": "simple"
            })
        if params.get("type") and params["type"].lower() != "all":
            condition["conditions"].append({
                "jsonPath": "$.type",
                "operatorType": "EQUALS",
                "value": params["type"].lower(),
                "type": "simple"
            })
        if params.get("tags"):
            for tag in params["tags"]:
                condition["conditions"].append({
                    "jsonPath": "$.tags",
                    "operatorType": "INOT_CONTAINS",
                    "value": tag,
                    "type": "simple"
                })
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"pets": pets}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_pet_add(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity.setdefault("created_at", datetime.utcnow().isoformat())
    if "tags" in entity and isinstance(entity["tags"], list):
        entity["tags"] = [tag.lower() for tag in entity["tags"]]
    try:
        # Example async enrichment with different entity model
        if "type" in entity and entity["type"]:
            metadata_condition = {
                "type": "simple",
                "jsonPath": "$.pet_type",
                "operatorType": "EQUALS",
                "value": entity["type"].lower()
            }
            pet_metadata = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="pet_metadata",
                entity_version=ENTITY_VERSION,
                condition=metadata_condition
            )
            if pet_metadata:
                entity["metadata"] = pet_metadata[0]
    except Exception:
        # catch exceptions here so they don't block persistence
        logger.exception("Failed to enrich pet metadata in workflow")
    return entity

async def process_pet_update(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity["updated_at"] = datetime.utcnow().isoformat()
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    # Additional enrichment or validation can be added here if needed
    return entity

async def process_add(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
            workflow=process_pet_add
        )
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"success": True, "petId": id_}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_update(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        id_ = data.get("id")
        if not id_:
            raise ValueError("Pet ID is required for update")
        # Check if update_item supports workflow argument
        # If not, remove workflow param
        # Here assuming it supports workflow
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=id_,
            workflow=process_pet_update
        )
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"success": True}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_delete(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        id_ = data.get("id")
        if id_ is None:
            raise ValueError("Pet ID missing for delete")
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=id_
        )
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"success": True}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

def generate_job_id() -> str:
    # Use utc timestamp with microseconds for uniqueness
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchParams)
async def pets_search(data: SearchParams):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_search(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPet)
async def pets_add(data: AddPet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_add(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/update", methods=["POST"])
@validate_request(UpdatePet)
async def pets_update(data: UpdatePet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_update(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/delete", methods=["POST"])
@validate_request(DeletePet)
async def pets_delete(data: DeletePet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_delete(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Pet not found"}), 404
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    async with entity_jobs_lock:
        job = entity_jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)