import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
import logging
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class WorkflowTrigger:
    event_type: str
    payload: Optional[Dict[str, Any]] = None

async def process_workflow_trigger(entity: dict) -> dict:
    """
    Workflow function for 'workflow_trigger' entity.
    Creates and manages a workflow job entity tracking async processing.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    job_entity = {
        "id": job_id,
        "status": "started",
        "requested_at": requested_at,
        "event_type": entity.get("event_type"),
        "payload": entity.get("payload"),
        "result": None,
        "started_at": None,
        "completed_at": None,
    }

    try:
        # Persist a new workflow_job entity to track job status
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="workflow_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity,
            workflow=None
        )
    except Exception as e:
        logger.error(f"Failed to create workflow_job entity for job_id {job_id}: {e}")
        # Fail workflow_trigger persistence by raising to avoid silent failure
        raise

    # Link job_id back to workflow_trigger entity for reference
    entity["job_id"] = job_id

    try:
        # Mark job as processing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="workflow_job",
            entity_version=ENTITY_VERSION,
            entity_id=job_id,
            entity_update={
                "status": "processing",
                "started_at": datetime.utcnow().isoformat() + "Z"
            },
        )

        # Perform external async operation
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post("https://httpbin.org/post", json=entity.get("payload") or {})
            response.raise_for_status()
            external_data = response.json()

        result_message = f"Hello World triggered by event '{entity.get('event_type')}'"

        # Mark job as completed with result
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="workflow_job",
            entity_version=ENTITY_VERSION,
            entity_id=job_id,
            entity_update={
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat() + "Z",
                "result": {
                    "message": result_message,
                    "external_response": external_data
                }
            },
        )
    except Exception as e:
        logger.exception(f"Workflow job {job_id} failed during processing.")
        # Mark job as failed with error info
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="workflow_job",
                entity_version=ENTITY_VERSION,
                entity_id=job_id,
                entity_update={
                    "status": "failed",
                    "completed_at": datetime.utcnow().isoformat() + "Z",
                    "result": {"error": str(e)},
                },
            )
        except Exception as inner_e:
            logger.error(f"Failed to update workflow_job status to failed for job_id {job_id}: {inner_e}")

    return entity

async def process_prototype_cyoda(entity: dict) -> dict:
    """
    Workflow function applied to 'prototype_cyoda' entity before persistence.
    Enriches entity asynchronously.
    """
    try:
        entity.setdefault("processed_at", datetime.utcnow().isoformat() + "Z")
        if "id" not in entity:
            entity["id"] = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("https://httpbin.org/uuid")
            response.raise_for_status()
            data = response.json()
            entity["external_uuid"] = data.get("uuid")

        entity["workflow_processed"] = True

    except Exception as e:
        logger.error(f"Error in workflow process_prototype_cyoda: {e}")

    return entity

@app.route("/workflow/trigger", methods=["POST"])
@validate_request(WorkflowTrigger)
async def trigger_workflow(data: WorkflowTrigger):
    """
    Endpoint to trigger workflow by creating a workflow_trigger entity.
    All async processing happens in workflow function process_workflow_trigger.
    """
    entity_data = {
        "event_type": data.event_type,
        "payload": data.payload or {},
    }

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="workflow_trigger",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_workflow_trigger,
        )
    except Exception as e:
        logger.error(f"Failed to add workflow_trigger entity: {e}")
        return jsonify({"status": "error", "message": "Failed to trigger workflow"}), 500

    return jsonify({
        "status": "started",
        "workflow_trigger_id": entity_id,
        "message": f"Workflow triggered for event '{data.event_type}'."
    })

@app.route("/workflow/result/<workflow_id>", methods=["GET"])
async def get_workflow_result(workflow_id):
    """
    Retrieves the status and result of a workflow job by workflow_id.
    """
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="workflow_job",
            entity_version=ENTITY_VERSION,
            entity_id=workflow_id,
        )
    except Exception as e:
        logger.error(f"Failed to get workflow_job entity for id {workflow_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve workflow result"}), 500

    if not job:
        return jsonify({
            "workflow_id": workflow_id,
            "status": "not_found",
            "message": "Workflow job ID not found"
        }), 404

    return jsonify({
        "workflow_id": workflow_id,
        "status": job.get("status"),
        "result": job.get("result"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
    })

# Example function demonstrating add with workflow for prototype_cyoda entity
async def add_prototype_cyoda_entity(data: dict) -> str:
    """
    Adds a 'prototype_cyoda' entity with async enrichment workflow.
    """
    entity_name = "prototype_cyoda"
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data,
            workflow=process_prototype_cyoda
        )
    except Exception as e:
        logger.error(f"Failed to add prototype_cyoda entity: {e}")
        raise
    return entity_id

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)