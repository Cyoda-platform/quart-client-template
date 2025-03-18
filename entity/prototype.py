#!/usr/bin/env python3
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

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

# In-memory store for jobs (mock persistence)
entity_jobs = {}

# Asynchronous function to simulate processing of the entity job
async def process_entity(job: dict, data: dict):
    """
    Process the entity job using an external API.
    This is a prototype; the external API and calculations are for demonstration purposes.
    """
    try:
        logger.info(f"Processing job: {job} with data: {data}")
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

        # Update job details with the result (In a real scenario, additional calculations would occur)
        job["status"] = "completed"
        job["completedAt"] = datetime.utcnow().isoformat() + "Z"
        job["result"] = result
        
        logger.info(f"Completed job with ID {job.get('job_id', 'unknown')}")
    except Exception as e:
        logger.exception(e)
        job["status"] = "error"
        job["error"] = str(e)
        # TODO: Improve error handling and possibly retry logic

# Endpoint to submit a new entity processing job
@app.route("/entity", methods=["POST"])
async def create_entity_job():
    """
    Create a new entity processing job. Expects JSON payload.
    """
    try:
        data = await request.get_json()
        # TODO: Validate the incoming data according to business requirements.
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"
        
        # Save job details in the in-memory store.
        entity_jobs[job_id] = {
            "status": "processing",
            "requestedAt": requested_at,
            "job_id": job_id
        }
        
        # Fire and forget the processing task.
        asyncio.create_task(process_entity(entity_jobs[job_id], data))
        
        logger.info(f"Created job with ID: {job_id}")
        return jsonify({"job_id": job_id, "status": "processing"}), 202
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
        job = entity_jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found."}), 404
        return jsonify(job), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

# Entry point of the prototype
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)