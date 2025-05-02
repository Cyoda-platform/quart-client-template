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
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class ProcessData:
    city: str  # expecting city name to query weather

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route("/process", methods=["POST"])
@validate_request(ProcessData)
async def post_process(data: ProcessData):
    """
    Just create the entity_job with city and let workflow function do the rest.
    """
    try:
        job_id = str(uuid.uuid4())
        # Compose initial entity with city and technical_id (job_id)
        entity = {
            "technical_id": job_id,
            "city": data.city
        }

        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity,
            )
        return jsonify({"processId": job_id, "status": "processing"}), 202

    except Exception as e:
        logger.exception("Failed to create job")
        return jsonify({"error": "Failed to create job"}), 500

@app.route("/result/<string:process_id>", methods=["GET"])
async def get_result(process_id):
    """Return processing status and result for the given process ID."""
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
    except Exception as e:
        logger.exception(f"Failed to get job {process_id}: {e}")
        return jsonify({"error": "Failed to retrieve job data"}), 500

    if not job:
        return jsonify({"error": "Process ID not found"}), 404

    response = {
        "processId": process_id,
        "status": job.get("status"),
        "result": job.get("result"),
    }
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)