from dataclasses import dataclass
import logging
from datetime import datetime

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

routes_bp = Blueprint('routes', __name__)

@dataclass
class ProcessData:
    name: str

EXTERNAL_API_URL = "https://api.agify.io"

async def fetch_external_data(name: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:  # set reasonable timeout
        try:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched external data for '{name}': {data}")
            return data
        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.error(f"Failed to fetch external data for '{name}': {e}")
            return {"error": "Failed to fetch external data"}

async def process_process_data(entity: dict):
    # Set initial status and timestamp
    entity['status'] = 'processing'
    entity['requestedAt'] = datetime.utcnow().isoformat()

    name = entity.get('name')
    if not name or not isinstance(name, str) or not name.strip():
        entity['status'] = 'failed'
        entity['result'] = {'error': 'Missing or invalid "name" attribute'}
        logger.error("process_process_data: Missing or invalid 'name' attribute in entity")
        return

    # Fetch and enrich entity with external data
    external_data = await fetch_external_data(name.strip())

    if 'error' in external_data:
        entity['status'] = 'failed'
        entity['result'] = external_data
        logger.error(f"process_process_data: External API error for '{name}': {external_data['error']}")
    else:
        entity['result'] = {
            "inputName": name.strip(),
            "predictedAge": external_data.get("age"),
            "count": external_data.get("count"),
            "source": "agify.io"
        }
        entity['status'] = 'completed'

@routes_bp.route("/process-data", methods=["POST"])
@validate_request(ProcessData)
async def process_data(data: ProcessData):
    try:
        entity_dict = data.__dict__
        # Defensive copy to avoid side effects outside workflow
        entity_to_add = dict(entity_dict)

        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="process_data",
            entity_version=ENTITY_VERSION,
            entity=entity_to_add
        )
        return jsonify({"id": str(entity_id)}), 202

    except Exception as e:
        logger.exception(f"Failed to start processing: {e}")
        return jsonify({"error": "Failed to start processing"}), 500

@routes_bp.route("/results/<string:workflow_id>", methods=["GET"])
async def get_results(workflow_id: str):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="process_data",
            entity_version=ENTITY_VERSION,
            technical_id=workflow_id
        )
        if not item:
            return jsonify({"error": "Workflow ID not found"}), 404

        # Defensive access with defaults
        status = item.get("status", "unknown")
        result = item.get("result", None)

        response = {
            "workflowId": workflow_id,
            "status": status,
            "result": result,
        }
        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"Error retrieving results for workflow {workflow_id}: {e}")
        return jsonify({"error": "Error retrieving results"}), 500