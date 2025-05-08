import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class WorkflowTrigger:
    event_type: str
    payload: Optional[Dict[str, Any]] = None

entity_jobs: Dict[str, Dict[str, Any]] = {}

async def process_set_started(entity: dict):
    entity["status"] = "processing"
    entity["started_at"] = datetime.utcnow().isoformat() + "Z"

async def process_external_call(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post("https://httpbin.org/post", json=entity.get("payload") or {})
            response.raise_for_status()
            entity["external_response"] = response.json()
    except Exception as e:
        entity["external_response"] = {"error": str(e)}
        logger.exception("External API call failed")

async def process_generate_result(entity: dict):
    event_type = entity.get("event_type", "")
    if "error" in entity.get("external_response", {}):
        entity["result"] = {"error": entity["external_response"]["error"]}
        entity["status"] = "failed"
    else:
        entity["result"] = {
            "message": f"Hello World triggered by event '{event_type}'",
            "external_response": entity.get("external_response")
        }
        entity["status"] = "completed"
    entity["completed_at"] = datetime.utcnow().isoformat() + "Z"

@app.route("/workflow/trigger", methods=["POST"])
@validate_request(WorkflowTrigger)
async def trigger_workflow(data: WorkflowTrigger):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity = {
        "workflow_id": job_id,
        "event_type": data.event_type,
        "payload": data.payload or {},
        "status": "started",
        "requested_at": requested_at,
        "result": None,
        "started_at": None,
        "completed_at": None,
        "external_response": None
    }
    entity_jobs[job_id] = entity

    asyncio.create_task(process_workflow_trigger(entity))

    return jsonify({
        "status": "started",
        "workflow_id": job_id,
        "message": f"Workflow triggered for event '{data.event_type}'."
    })

@app.route("/workflow/result/<workflow_id>", methods=["GET"])
async def get_workflow_result(workflow_id):
    job = entity_jobs.get(workflow_id)
    if not job:
        return jsonify({
            "workflow_id": workflow_id,
            "status": "not_found",
            "message": "Workflow ID not found"
        }), 404

    return jsonify({
        "workflow_id": job["workflow_id"],
        "status": job["status"],
        "result": job["result"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
    })

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)