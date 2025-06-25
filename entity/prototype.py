```python
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache for workflow states and results.
# Structure: {workflowId: {"status": str, "requestedAt": datetime, "result": dict or None}}
entity_jobs = {}

# Example real external API to fetch some data for demonstration:
# Using a public API for placeholder: https://api.agify.io?name=michael
EXTERNAL_API_URL = "https://api.agify.io"


async def fetch_external_data(name: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            data = response.json()
            logger.info(f"External API data fetched for name={name}: {data}")
            return data
        except httpx.HTTPError as e:
            logger.exception(f"External API request failed: {e}")
            # Return minimal error info for prototype
            return {"error": "Failed to fetch external data"}


async def process_entity(entity_jobs_cache: dict, workflow_id: str, input_data: dict):
    try:
        # Example: Assume input_data has {"name": "<some_name>"}
        name = input_data.get("name", "unknown")

        # Step 1: Fetch external data (age prediction by name)
        external_data = await fetch_external_data(name)

        # Step 2: Example calculation: Compose result combining input + external data
        result = {
            "inputName": name,
            "predictedAge": external_data.get("age"),
            "count": external_data.get("count"),
            "source": "agify.io"
        }

        # Simulate some processing delay
        await asyncio.sleep(2)

        # Update the job cache with result and status
        entity_jobs_cache[workflow_id]["status"] = "completed"
        entity_jobs_cache[workflow_id]["result"] = result
        logger.info(f"Workflow {workflow_id} completed with result: {result}")

    except Exception as e:
        logger.exception(f"Error processing workflow {workflow_id}: {e}")
        entity_jobs_cache[workflow_id]["status"] = "failed"
        entity_jobs_cache[workflow_id]["result"] = {"error": str(e)}


@app.route("/process-data", methods=["POST"])
async def process_data():
    try:
        data = await request.get_json(force=True)
        # Generate a new workflow/job id
        workflow_id = str(uuid.uuid4())
        requested_at = datetime.utcnow()

        # Initialize job status in cache
        entity_jobs[workflow_id] = {
            "status": "processing",
            "requestedAt": requested_at,
            "result": None
        }

        # Fire and forget the processing task
        asyncio.create_task(process_entity(entity_jobs, workflow_id, data))

        return jsonify({"status": "processing", "workflowId": workflow_id}), 202

    except Exception as e:
        logger.exception(f"Failed to start processing: {e}")
        return jsonify({"error": "Failed to start processing"}), 500


@app.route("/results/<workflow_id>", methods=["GET"])
async def get_results(workflow_id):
    job = entity_jobs.get(workflow_id)
    if not job:
        return jsonify({"error": "Workflow ID not found"}), 404

    response = {
        "workflowId": workflow_id,
        "status": job["status"],
        "result": job["result"],
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
