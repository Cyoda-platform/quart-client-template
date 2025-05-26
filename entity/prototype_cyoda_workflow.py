from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class ProcessRequest:
    inputData: dict

async def call_external_api(name: str) -> dict:
    url = "https://api.agify.io"
    params = {"name": name}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.exception(f"External API call failed: {e}")
        raise

# Workflow function - processes entity_jobs before persistence
async def process_entity_jobs(entity: dict):
    """
    This function is invoked asynchronously before persisting the entity.
    It modifies the entity in place, including status updates and results.
    """
    try:
        input_data = entity.get("inputData", {})
        name = input_data.get("name")
        if not name:
            raise ValueError("Missing 'name' in inputData")

        # Call external API asynchronously
        result = await call_external_api(name)

        # Update entity state directly
        entity["status"] = "completed"
        entity["result"] = {
            "inputName": name,
            "predictedAge": result.get("age"),
            "count": result.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
        entity["message"] = "Processing completed successfully"

    except Exception as e:
        logger.exception(f"Error processing entity_jobs id={entity.get('id')}: {e}")
        entity["status"] = "failed"
        entity["message"] = str(e)

    return entity

@app.route("/process", methods=["POST"])
@validate_request(ProcessRequest)
async def post_process(data: ProcessRequest):
    input_data = data.inputData
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    # Initial entity state, minimal info
    job_entity = {
        "id": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "inputData": input_data,
    }

    # Add entity with workflow; workflow will execute asynchronously before persistence
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_jobs",
        entity_version=ENTITY_VERSION,
        entity=job_entity,
        workflow=process_entity_jobs,
    )

    # Return immediately, processing happens in workflow before persistence
    return jsonify({"processId": job_id, "status": "processing", "message": "Processing started"}), 202

@app.route("/result/<process_id>", methods=["GET"])
async def get_result(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_jobs",
            entity_version=ENTITY_VERSION,
            technical_id=process_id,
        )
        if not job:
            return jsonify({"message": f"Process ID {process_id} not found"}), 404

        response = {
            "processId": process_id,
            "status": job.get("status"),
            "message": job.get("message", ""),
        }
        if job.get("status") == "completed":
            response["result"] = job.get("result")

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"Error retrieving result for process ID {process_id}: {e}")
        return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)