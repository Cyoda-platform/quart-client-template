import asyncio
import uuid
from datetime import datetime
import logging
from dataclasses import dataclass

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# In-memory cache for jobs
entity_jobs = {}

# External API URL - using a real API that echoes POST requests.
EXTERNAL_API_URL = "https://postman-echo.com/post"

@dataclass
class DataQuery:
    query: str  # Only primitive type is allowed

async def process_entity(job_id: str, query: str):
    """
    Process the job by calling an external API.
    Updates the job result in the in-memory cache.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Make a POST call to external API with the provided query
            response = await client.post(EXTERNAL_API_URL, json={"query": query})
            response.raise_for_status()
            result = response.json()

            # Update the job status and result.
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["result"] = result
            logger.info(f"Job {job_id} completed with result: {result}")
    except Exception as e:
        # Log the exception and update the job status as failed.
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        # TODO: In a production system, implement retry logic or failover procedures.

@app.route("/hello", methods=["GET"])
async def hello():
    """
    GET /hello
    Returns a simple greeting message.
    """
    return jsonify({"message": "Hello, World!"}), 200

# For POST endpoints the route decorator must come first then validation.
@app.route("/data", methods=["POST"])
@validate_request(DataQuery)  # Workaround: for POST endpoints, validation is placed after the route decorator.
async def data(data: DataQuery):
    """
    POST /data
    Accepts a query for external data retrieval and starts async processing.
    """
    query = data.query

    # Generate a unique job_id and record the job in the local cache.
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
    }

    logger.info(f"Received job {job_id} with query: {query}")

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, query))

    return jsonify({"job_id": job_id, "status": "processing", "requestedAt": requested_at}), 202

@app.route("/job/<job_id>", methods=["GET"])
async def get_job(job_id):
    """
    GET /job/<job_id>
    Retrieves the status and result of a previously submitted job.
    """
    job = entity_jobs.get(job_id)
    if not job:
        abort(404, description="Job not found.")

    return jsonify({"job_id": job_id, "job": job}), 200

if __name__ == '__main__':
    # Entry point to run the application
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)