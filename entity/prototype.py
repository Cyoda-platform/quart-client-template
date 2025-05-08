from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence
entity_job: Dict[str, dict] = {}

# Simple state machine states for the workflow
STATE_IDLE = "idle"
STATE_PROCESSING = "processing"
STATE_COMPLETED = "completed"

@dataclass
class EventData:
    message: str = None  # optional string, primitive type


async def fetch_external_greeting() -> str:
    """
    Fetch greeting message from a real external API.
    Using https://api.github.com/zen as a placeholder for an external API returning a string.
    TODO: Replace with a proper greeting API if desired.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/zen")
            response.raise_for_status()
            # The GitHub zen API returns a short zen phrase as plain text
            return response.text.strip()
    except Exception as e:
        logger.exception(e)
        return "Hello World!"  # Fallback greeting


async def process_entity(job_store: Dict[str, dict], job_id: str, event_data: dict):
    """
    Simulates processing the entity workflow using a state machine.
    1. Fetch external data (greeting)
    2. Update state machine accordingly
    """
    try:
        job = job_store[job_id]
        job["status"] = STATE_PROCESSING
        job["startedAt"] = datetime.utcnow().isoformat()

        # Simulate workflow step: fetch external greeting
        external_greeting = await fetch_external_greeting()

        # Business logic to combine event_data with greeting
        # For prototype, just echo event_data if provided, else use external greeting
        user_msg = event_data.get("message") or external_greeting

        # Compose final output
        output = f"{user_msg}"

        # Update job state and output
        job["status"] = STATE_COMPLETED
        job["completedAt"] = datetime.utcnow().isoformat()
        job["output"] = output
    except Exception as e:
        logger.exception(e)
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)


@app.route("/api/hello-world/trigger", methods=["POST"])
@validate_request(EventData)  # validation last for POST (issue workaround)
async def trigger_hello_world(data: EventData):
    """
    POST endpoint to trigger the Hello World workflow.
    Accepts dynamic event_data JSON.
    Returns workflow_id and status.
    """
    try:
        event_data = data.__dict__ if data else {}
        # Generate a simple unique workflow id using timestamp + counter
        workflow_id = f"job-{int(datetime.utcnow().timestamp()*1000)}"

        # Store initial job state
        entity_job[workflow_id] = {
            "status": STATE_IDLE,
            "requestedAt": datetime.utcnow().isoformat(),
            "event_data": event_data,
        }

        # Fire and forget the processing task
        asyncio.create_task(process_entity(entity_job, workflow_id, event_data))

        return jsonify({"workflow_id": workflow_id, "status": "initiated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to trigger workflow"}), 500


@app.route("/api/hello-world/result/<string:workflow_id>", methods=["GET"])
# validation first for GET (issue workaround)
async def get_workflow_result(workflow_id: str):
    """
    GET endpoint to retrieve workflow result by workflow_id.
    Returns current state and output.
    """
    job = entity_job.get(workflow_id)
    if not job:
        return jsonify({"error": "Workflow ID not found"}), 404

    # Return relevant job info (state machine status, output if available)
    response = {
        "workflow_id": workflow_id,
        "state": job.get("status", "unknown"),
        "output": job.get("output", None),
        "timestamp": job.get("completedAt") or job.get("requestedAt"),
    }
    return jsonify(response)


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
