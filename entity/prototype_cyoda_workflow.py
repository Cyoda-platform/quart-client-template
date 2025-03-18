#!/usr/bin/env python3
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

# Workflow function for processing the entity.
# This function is applied asynchronously to the entity before it is persisted.
# It takes the entity data as the only argument and modifies it directly.
async def process_entity(entity: dict):
    """
    Process the entity job by calling an external API
    and modifying the entity state directly.
    This function runs asynchronously before the entity is persisted.
    """
    try:
        job_id = entity.get("job_id")
        payload = entity.get("payload", {})
        logger.info(f"Workflow started for job_id: {job_id} with payload: {payload}")
        # Call an external API to get a Chuck Norris joke.
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.chucknorris.io/jokes/random")
            if response.status_code == 200:
                result = response.json().get("value", "No joke found.")
            else:
                result = "Error retrieving joke."
                logger.error(f"External API error for job_id {job_id}: {response.status_code}")
        # Simulate processing delay
        await asyncio.sleep(1)
        completed_at = datetime.utcnow().isoformat() + "Z"
        # Modify the entity state directly. These changes will be persisted.
        entity["status"] = "completed"
        entity["completedAt"] = completed_at
        entity["result"] = result
        logger.info(f"Workflow completed for job_id: {job_id}")
    except Exception as e:
        logger.exception(f"Workflow error for job_id {entity.get('job_id')}: {e}")
        entity["status"] = "error"
        entity["error"] = str(e)
    return entity

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
            workflow=process_entity  # Workflow function that performs asynchronous logic
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

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)