```python
import asyncio
import logging
from datetime import datetime
from typing import Dict

from quart import Quart, jsonify, request
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Simple in-memory cache for storing the latest message per job_id
# Structure: {job_id: {"status": str, "requestedAt": datetime, "message": str}}
entity_job: Dict[str, Dict] = {}


async def process_entity(job_id: str, payload: dict):
    try:
        # Simulate external API call to get a greeting message
        # Using a real API: httpbin.org/post echoes the data back, so we use it as a placeholder
        async with httpx.AsyncClient() as client:
            # POST the action to httpbin.org/post, just to simulate external call
            response = await client.post("https://httpbin.org/post", json=payload)
            response.raise_for_status()

            # TODO: Replace above API with real business logic or external API if specified
            # For now, we just ignore the response and return "Hello World"

        # Update the job status and message
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["message"] = "Hello World"
        logger.info(f"Processed job {job_id} successfully.")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["message"] = None
        logger.exception(f"Failed processing job {job_id}: {e}")


@app.route("/hello", methods=["POST"])
async def post_hello():
    data = await request.get_json()
    if not data or data.get("action") != "generate_hello":
        return jsonify({"error": "Invalid request body or action"}), 400

    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))  # simple unique job_id
    requested_at = datetime.utcnow()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at, "message": None}

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))

    # Respond immediately with job id and status
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/hello", methods=["GET"])
async def get_hello():
    # Return the latest completed message, or info if none available
    # We get the most recently requested completed job if any
    completed_jobs = [
        (job_id, info)
        for job_id, info in entity_job.items()
        if info["status"] == "completed" and info["message"] is not None
    ]
    if not completed_jobs:
        return jsonify({"message": None, "info": "No completed 'Hello World' message found yet."}), 404

    # Sort by requestedAt descending to get latest
    completed_jobs.sort(key=lambda x: x[1]["requestedAt"], reverse=True)
    latest_job = completed_jobs[0][1]

    return jsonify({"message": latest_job["message"]})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```