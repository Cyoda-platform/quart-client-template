#!/usr/bin/env python3
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
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

# Asynchronous function to simulate processing of the entity job
async def process_entity(job_id: str, data: dict):
    """
    Process the entity job using an external API.
    This is a prototype; the external API and calculations are for demonstration purposes.
    """
    try:
        logger.info(f"Processing job_id: {job_id} with data: {data}")
        # Example: calling a real external API to get a Chuck Norris joke.
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.chucknorris.io/jokes/random")
            if response.status_code == 200:
                result = response.json().get("value", "No joke found.")
            else:
                result = "Error retrieving joke."
                logger.error(f"External API error: {response.status_code}")
        
        # Simulate processing delay
        await asyncio.sleep(1)

        # Prepare updated job details with the result
        completed_at = datetime.utcnow().isoformat() + "Z"
        updated_job = {
            "status": "completed",
            "completedAt": completed_at,
            "result": result
        }
        logger.info(f"Completed job with ID {job_id}")
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=updated_job,
            technical_id=job_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        error_update = {
            "status": "error",
            "error": str(e)
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                entity=error_update,
                technical_id=job_id,
                meta={}
            )
        except Exception as inner_e:
            logger.exception(inner_e)

# Endpoint to submit a new entity processing job
# Workaround for quart-schema decorator ordering: for POST requests, @route comes first then @validate_request.
@app.route("/entity", methods=["POST"])
@validate_request(EntityJobRequest)
async def create_entity_job(data: EntityJobRequest):
    """
    Create a new entity processing job. Expects JSON payload.
    """
    try:
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"
        job = {
            "status": "processing",
            "requestedAt": requested_at,
            "job_id": job_id
        }
        # Replace local cache with a call to external service add_item
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=job
        )
        # Fire and forget the processing task
        asyncio.create_task(process_entity(job_id, data.__dict__))
        logger.info(f"Created job with ID: {job_id}")
        # Return only the id in the response as the result will be retrieved in a separate endpoint
        return jsonify({"job_id": id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

# Endpoint to fetch the status of a specific job by its job_id
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
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Entry point of the prototype
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)