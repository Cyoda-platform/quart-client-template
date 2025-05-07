from dataclasses import dataclass
from typing import Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence for entities and workflows
entities_state: Dict[str, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

# Example external API: use a public API for demonstration, e.g. JSONPlaceholder
EXTERNAL_API_URL = "https://jsonplaceholder.typicode.com/todos/1"


@dataclass
class TriggerWorkflowRequest:
    event_type: str
    payload: Dict[str, Any]  # dynamic dict accepted


@dataclass
class ProcessDataRequest:
    input_data: Dict[str, Any]  # dynamic dict accepted


async def fetch_external_data() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched external data successfully")
            return data
        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch external data: {e}")
            return {}


async def process_workflow(job_id: str, entity_id: str, event_type: str, payload: Dict[str, Any]):
    try:
        # Mark job as processing
        entity_jobs[job_id]["status"] = "processing"
        logger.info(f"Started processing job {job_id} for entity {entity_id}")

        # TODO: Implement more complex workflow logic if needed

        # Example: Fetch external data as part of workflow
        external_data = await fetch_external_data()

        # Simulate some processing combining payload & external data
        processed_result = {
            "hello_message": "Hello World!",
            "event_type": event_type,
            "payload_received": payload,
            "external_data": external_data,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }

        # Update entity state with processed result and set a new workflow state
        entities_state[entity_id] = {
            "current_state": "completed",
            "data": processed_result,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        # Update job status
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = processed_result
        logger.info(f"Completed processing job {job_id} for entity {entity_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Error processing job {job_id} for entity {entity_id}: {e}")


async def process_data(job_id: str, entity_id: str, input_data: Dict[str, Any]):
    try:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}

        # Example: simulate calling an external API that does calculations
        # Here we'll call the same example API, but in real case, it could be any external calculation API
        async with httpx.AsyncClient() as client:
            # TODO: Replace with real external API for calculation if specified
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            external_result = response.json()

        # Simulate processing results combining external results and input_data
        result = {
            "calculation_result": external_result,
            "input_data_received": input_data,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }

        # Update entity state with processing results
        entities_state[entity_id] = {
            "current_state": "data_processed",
            "data": result,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = result
        logger.info(f"Completed data processing job {job_id} for entity {entity_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Error processing data job {job_id} for entity {entity_id}: {e}")


@app.route("/api/entity/<string:entity_id>/trigger", methods=["POST"])
@validate_request(TriggerWorkflowRequest)  # Validation last for POST method (issue workaround)
async def trigger_workflow(entity_id, data: TriggerWorkflowRequest):
    job_id = f"job-{datetime.utcnow().timestamp()}-{entity_id}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat() + "Z"}

    # Fire and forget the processing task
    asyncio.create_task(process_workflow(job_id, entity_id, data.event_type, data.payload))

    return jsonify(
        {
            "status": "success",
            "message": "Workflow triggered",
            "workflow_id": job_id,
        }
    )


# No validation decorator for GET without query params - per spec
@app.route("/api/entity/<string:entity_id>/state", methods=["GET"])
async def get_entity_state(entity_id):
    state = entities_state.get(entity_id)
    if not state:
        return jsonify({"status": "error", "message": "Entity not found"}), 404

    response = {
        "entity_id": entity_id,
        "current_state": state.get("current_state"),
        "data": state.get("data"),
        "last_updated": state.get("last_updated"),
    }
    return jsonify(response)


@app.route("/api/entity/<string:entity_id>/process", methods=["POST"])
@validate_request(ProcessDataRequest)  # Validation last for POST method (issue workaround)
async def submit_data_for_processing(entity_id, data: ProcessDataRequest):
    job_id = f"proc-{datetime.utcnow().timestamp()}-{entity_id}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat() + "Z"}

    asyncio.create_task(process_data(job_id, entity_id, data.input_data))

    return jsonify({"status": "success", "message": "Processing started", "job_id": job_id})


if __name__ == "__main__":
    import sys

    # Configure logging to console
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
