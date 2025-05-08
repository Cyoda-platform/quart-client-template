import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
import logging
from quart import Blueprint, jsonify
from quart_schema import validate_request
from dataclasses import dataclass

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class WorkflowTrigger:
    event_type: str
    payload: Optional[Dict[str, Any]] = None

@routes_bp.route("/workflow/trigger", methods=["POST"])
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
            )
    except Exception as e:
        logger.error(f"Failed to add workflow_trigger entity: {e}")
        return jsonify({"status": "error", "message": "Failed to trigger workflow"}), 500

    return jsonify({
        "status": "started",
        "workflow_trigger_id": entity_id,
        "message": f"Workflow triggered for event '{data.event_type}'."
    })

@routes_bp.route("/workflow/result/<workflow_id>", methods=["GET"])
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
            )
    except Exception as e:
        logger.error(f"Failed to add prototype_cyoda entity: {e}")
        raise
    return entity_id