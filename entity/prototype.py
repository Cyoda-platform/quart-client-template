```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "cache" for process status and results (async-safe by design of Quart event loop)
entity_jobs = {}


async def call_external_api(input_value: str) -> dict:
    """
    Example external API call - fetch some real data.
    Here we use https://api.agify.io which predicts age from a name.
    This is a placeholder for your real external API or calculation.
    """
    url = "https://api.agify.io"
    params = {"name": input_value}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.exception(f"External API call failed: {e}")
        raise


async def process_entity(job_id: str, input_data: dict):
    """
    Process business logic, including external API calls and calculations.
    Update the entity_jobs cache with results or errors.
    """
    try:
        # Example: extract a name from inputData to call external API
        name = input_data.get("name")
        if not name:
            raise ValueError("Missing 'name' in inputData")

        result = await call_external_api(name)

        # Example business logic: augment result with timestamp
        processed_result = {
            "inputName": name,
            "predictedAge": result.get("age"),
            "count": result.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = processed_result
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"

    except Exception as e:
        logger.exception(f"Processing failed for job {job_id}: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["message"] = str(e)


@app.route("/process", methods=["POST"])
async def post_process():
    """
    Starts processing the input data.
    Expects JSON in the format: { "inputData": { ... } }
    """
    try:
        data = await request.get_json(force=True)
        input_data = data.get("inputData")
        if not isinstance(input_data, dict):
            return jsonify({"message": "'inputData' must be an object"}), 400

        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"

        # Initialize job state
        entity_jobs[job_id] = {
            "status": "processing",
            "requestedAt": requested_at,
        }

        # Fire and forget processing task
        asyncio.create_task(process_entity(job_id, input_data))

        return jsonify({"processId": job_id, "status": "processing", "message": "Processing started"}), 202

    except Exception as e:
        logger.exception(f"Error in /process endpoint: {e}")
        return jsonify({"message": "Invalid request or internal error"}), 500


@app.route("/result/<process_id>", methods=["GET"])
async def get_result(process_id):
    """
    Retrieve the status and result of a processing job by processId.
    """
    job = entity_jobs.get(process_id)
    if not job:
        return jsonify({"message": f"Process ID {process_id} not found"}), 404

    # Compose response
    response = {
        "processId": process_id,
        "status": job.get("status"),
        "message": job.get("message", ""),
    }
    if job.get("status") == "completed":
        response["result"] = job.get("result")

    return jsonify(response), 200


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
