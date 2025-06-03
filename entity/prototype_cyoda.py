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

# Request models
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
        # Build condition for search based on params
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
        # The result is a list of pets
        async with entity_jobs_lock:
            entity_job["status"] = "completed"
            entity_job["result"] = {"pets": pets}
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_job["status"] = "failed"
            entity_job["error"] = str(e)

async def process_add(entity_job: Dict[str, Any], data: Dict[str, Any]):
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data
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
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
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
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchParams)  # workaround: place last for POST due to library defect
async def pets_search(data: SearchParams):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_search(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPet)  # workaround: place last for POST due to library defect
async def pets_add(data: AddPet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_add(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/update", methods=["POST"])
@validate_request(UpdatePet)  # workaround: place last for POST due to library defect
async def pets_update(data: UpdatePet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_update(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/delete", methods=["POST"])
@validate_request(DeletePet)  # workaround: place last for POST due to library defect
async def pets_delete(data: DeletePet):
    job_id = generate_job_id()
    entity_job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    async with entity_jobs_lock:
        entity_jobs[job_id] = entity_job
    asyncio.create_task(process_delete(entity_job, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/<string:pet_id>", methods=["GET"])  # id now string
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