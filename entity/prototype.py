from dataclasses import dataclass
from typing import Optional, Dict, Any

import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class WorkflowTrigger:
    event_type: str
    payload: Optional[Dict[str, Any]] = None

# In-memory storage for workflow entities
entity_jobs: Dict[str, Dict[str, Any]] = {}

async def process_entity(job_id: str, event_type: str, payload: dict):
    """
    Simulate workflow processing triggered by an event.
    For demonstration, it calls a real external API (httpbin.org/post)
    to simulate external data retrieval or calculation.
    """
    try:
        # Mark job as processing
        entity_jobs[job_id]["status"] = "processing"
        entity_jobs[job_id]["started_at"] = datetime.utcnow().isoformat() + "Z"

        # For the sake of example, we POST payload to httpbin.org/post to simulate external API call
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post("https://httpbin.org/post", json=payload or {})
            response.raise_for_status()
            external_data = response.json()
            # TODO: Replace with actual business logic or external API call as needed

        # Simulate generating output (Hello World message)
        result_message = f"Hello World triggered by event '{event_type}'"

        # Store the result
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        entity_jobs[job_id]["result"] = {
            "message": result_message,
            "external_response": external_data  # Included for debug/demo purposes
        }

        logger.info(f"Workflow {job_id} completed successfully.")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        entity_jobs[job_id]["result"] = {"error": str(e)}
        logger.exception(f"Workflow {job_id} failed with exception.")

@app.route("/workflow/trigger", methods=["POST"])
@validate_request(WorkflowTrigger)  # Validation must be last decorator on POST - workaround for quart-schema issue
async def trigger_workflow(data: WorkflowTrigger):
    """
    POST /workflow/trigger
    Triggers the entity workflow by sending an event.
    """
    event_type = data.event_type
    payload = data.payload or {}

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    entity_jobs[job_id] = {
        "status": "started",
        "requested_at": requested_at,
        "result": None,
        "started_at": None,
        "completed_at": None,
    }

    # Fire and forget processing
    asyncio.create_task(process_entity(job_id, event_type, payload))

    return jsonify({
        "status": "started",
        "workflow_id": job_id,
        "message": f"Workflow triggered for event '{event_type}'."
    })

@app.route("/workflow/result/<workflow_id>", methods=["GET"])
# Validation workaround: validation must come first on GET routes but no validation needed here since no query params or body
async def get_workflow_result(workflow_id):
    """
    GET /workflow/result/{workflow_id}
    Retrieves the result or status of a previously triggered workflow.
    """
    job = entity_jobs.get(workflow_id)
    if not job:
        return jsonify({
            "workflow_id": workflow_id,
            "status": "not_found",
            "message": "Workflow ID not found"
        }), 404

    return jsonify({
        "workflow_id": workflow_id,
        "status": job["status"],
        "result": job["result"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
    })

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)