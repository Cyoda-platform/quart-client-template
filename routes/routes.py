from common.grpc_client.grpc_client import grpc_stream
from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class ProcessDataRequest:
    postId: str  # expecting postId as string for external API param

@app.route("/process-data", methods=["POST"])
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
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=initial_entity,
        )

    # No need for explicit asyncio.create_task or background tasks here
    # Workflow handles async processing before persistence

    return jsonify({"processId": job_id, "status": "processing"}), 202

@app.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
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

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)