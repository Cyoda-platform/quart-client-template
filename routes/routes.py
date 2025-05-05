from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

from quart import Blueprint, jsonify
from quart_schema import validate_request
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION
from common.service.entity_service_interface import EntityService

# Logger setup
logger = logging.getLogger(__name__)

# Blueprint initialization
routes_bp = Blueprint("routes", __name__)

# BeanFactory and service initialization
factory = BeanFactory(config={"CHAT_REPOSITORY": "cyoda"})
entity_service: EntityService = factory.get_services()["entity_service"]
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]


@dataclass
class ProcessDataRequest:
    postId: str  # expecting postId as string for external API param

@routes_bp.route("/process-data", methods=["POST"])
@validate_request(ProcessDataRequest)  # validation last in post method (issue workaround)
async def process_data(data: ProcessDataRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    # Initial entity includes inputData so workflow can access original inputs
    initial_entity = {
        "status": "processing",
        "requestedAt": requested_at,
        "message": None,
        "result": None,
        "technical_id": job_id,
        "inputData": data.__dict__,  # pass original inputs for workflow
    }

    # Add item with workflow function which will perform async processing before persistence
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=initial_entity,
    )

    # No need for explicit asyncio.create_task or background tasks here
    # Workflow handles async processing before persistence

    return jsonify({"processId": job_id, "status": "processing"}), 202

@routes_bp.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=process_id,
        )
    except Exception as e:
        logger.warning(f"Error retrieving process_id {process_id}: {e}")
        return jsonify({"message": "processId not found"}), 404

    if not job:
        return jsonify({"message": "processId not found"}), 404

    resp = {
        "processId": process_id,
        "status": job.get("status"),
        "result": job.get("result"),
        "message": job.get("message"),
    }
    return jsonify(resp), 200
