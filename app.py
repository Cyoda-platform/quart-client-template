from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create Quart app and initialize QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Dataclass for POST request validation (use only primitives)
from dataclasses import dataclass
@dataclass
class EntityJobRequest:
    message: str  # TODO: Replace with actual fields as required

# Endpoint to submit a new entity processing job.
# The asynchronous processing logic is moved to the workflow function.
@app.route("/entity", methods=["POST"])
@validate_request(EntityJobRequest)
async def create_entity_job(data: EntityJobRequest):
    """
    Create a new entity processing job.
    The workflow function (process_entity) processes the entity asynchronously
    before it is persisted.
    """
    try:
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"
        # Prepare the initial job entity with the payload.
        job = {
            "job_id": job_id,
            "status": "processing",
            "requestedAt": requested_at,
            "payload": data.__dict__
        }
        # The workflow function (process_entity) will be applied to the entity directly
        # and its modifications will be persisted.
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=job,
            )
        logger.info(f"Created job with ID: {job_id}")
        # Return the job identifier.
        return jsonify({"job_id": id}), 202
    except Exception as e:
        logger.exception(f"Error creating job: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoint to fetch the status of a specific job by its job_id.
@app.route("/entity/<job_id>", methods=["GET"])
async def get_entity_job_status(job_id):
    """
    Retrieve the status of the processing job.
    """
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"error": "Job not found."}), 404
        return jsonify(job), 200
    except Exception as e:
        logger.exception(f"Error retrieving job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)