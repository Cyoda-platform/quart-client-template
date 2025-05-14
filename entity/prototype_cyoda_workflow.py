import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from quart import Quart, request, jsonify
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
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    photoUrls: Optional[List[str]] = None

@dataclass
class PetUpdate:
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    photoUrls: Optional[List[str]] = None

@dataclass
class PetDelete:
    id: str

entity_jobs: Dict[str, Dict[str, Any]] = {}

PET_ENTITY_NAME = "pet"

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow function applied to pet entity asynchronously before persistence.
    # Modify entity state here, add related entities of different models if needed.
    entity["processed"] = True
    entity["processedAt"] = datetime.utcnow().isoformat()
    # Example: Add a supplementary entity (commented out - enable as needed)
    # await entity_service.add_item(
    #     token=cyoda_auth_service,
    #     entity_model="pet_history",
    #     entity_version=ENTITY_VERSION,
    #     entity={"pet_name": entity.get("name"), "event": "added", "timestamp": entity["processedAt"]}
    # )
    return entity

async def process_add_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        payload = {
            "name": data.get("name"),
            "photoUrls": data.get("photoUrls") or [],
            "status": data.get("status"),
            "category": {"name": data.get("type")} if data.get("type") else None,
        }
        if payload["category"] is None:
            payload.pop("category")

        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=payload,
            workflow=process_pet
        )

        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"id": str(pet_id), "message": "Pet add job submitted"},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error adding pet")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })

async def process_update_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        pet_id = data.get("id")
        if not pet_id:
            raise ValueError("Pet id is required for update")

        payload = {
            "name": data.get("name"),
            "photoUrls": data.get("photoUrls") or [],
            "status": data.get("status"),
            "category": {"name": data.get("type")} if data.get("type") else None,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if "category" in payload and payload["category"] is None:
            payload.pop("category")

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=payload,
            technical_id=str(pet_id),
            meta={}
        )
        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"message": "Pet update job submitted"},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error updating pet")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })

async def process_delete_pet(data: Dict[str, Any], job_id: str) -> None:
    try:
        pet_id = data.get("id")
        if not pet_id:
            raise ValueError("Pet id is required for delete")

        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id),
            meta={}
        )
        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"message": "Pet delete job submitted"},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error deleting pet")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })

async def process_search(criteria: Dict[str, Any]) -> None:
    job_id = criteria.get("job_id")
    try:
        conditions = []
        if criteria.get("status"):
            conditions.append({
                "jsonPath": "$.status",
                "operatorType": "EQUALS",
                "value": criteria["status"],
                "type": "simple"
            })
        if criteria.get("type"):
            conditions.append({
                "jsonPath": "$.category.name",
                "operatorType": "IEQUALS",
                "value": criteria["type"],
                "type": "simple"
            })
        if criteria.get("name"):
            conditions.append({
                "jsonPath": "$.name",
                "operatorType": "ICONTAINS",
                "value": criteria["name"],
                "type": "simple"
            })

        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": conditions
            }
        } if conditions else None

        if condition:
            pets = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            pets = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
            )

        entity_jobs[job_id].update({
            "status": "completed",
            "result": {"pets": pets},
            "completedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Error processing pet search")
        entity_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    job_id = f"search_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    criteria = data.__dict__.copy()
    criteria["job_id"] = job_id
    asyncio.create_task(process_search(criteria))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)
async def pets_add(data: PetAdd):
    job_id = f"add_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    payload = data.__dict__.copy()
    asyncio.create_task(process_add_pet(payload, job_id))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/update", methods=["POST"])
@validate_request(PetUpdate)
async def pets_update(data: PetUpdate):
    job_id = f"update_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    payload = data.__dict__.copy()
    asyncio.create_task(process_update_pet(payload, job_id))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/delete", methods=["POST"])
@validate_request(PetDelete)
async def pets_delete(data: PetDelete):
    job_id = f"delete_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    payload = data.__dict__.copy()
    asyncio.create_task(process_delete_pet(payload, job_id))
    return jsonify({"job_id": job_id}), 202

@app.route("/pets/job_status/<job_id>", methods=["GET"])
async def job_status(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception("Failed to retrieve pet")
        return jsonify({"error": "Failed to retrieve pet"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)