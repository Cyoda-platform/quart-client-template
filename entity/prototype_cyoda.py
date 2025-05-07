from dataclasses import dataclass
from typing import Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence for jobs only (entity state replaced by entity_service)
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

        # Update entity state using entity_service
        # Retrieve existing entity data if any
        try:
            existing_entity = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                technical_id=entity_id,
            )
        except Exception:
            existing_entity = None

        new_entity_data = {
            "current_state": "completed",
            "data": processed_result,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        # Update or add the entity
        if existing_entity:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                entity=new_entity_data,
                technical_id=entity_id,
                meta={},
            )
        else:
            # Add new entity with provided entity_id as technical_id might not be supported directly,
            # so add new and ignore id usage here (skip if no direct support)
            # Since add_item returns new id, but we want to preserve entity_id, skip add if no direct support
            pass

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

        # Update entity state using entity_service
        try:
            existing_entity = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                technical_id=entity_id,
            )
        except Exception:
            existing_entity = None

        new_entity_data = {
            "current_state": "data_processed",
            "data": result,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        if existing_entity:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                entity=new_entity_data,
                technical_id=entity_id,
                meta={},
            )
        else:
            # Same note as above: no direct add with custom id, skip if no support
            pass

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = result
        logger.info(f"Completed data processing job {job_id} for entity {entity_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Error processing data job {job_id} for entity {entity_id}: {e}")


@app.route("/api/entity/<string:entity_id>/trigger", methods=["POST"])
@validate_request(TriggerWorkflowRequest)
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


@app.route("/api/entity/<string:entity_id>/state", methods=["GET"])
async def get_entity_state(entity_id):
    try:
        state = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception:
        return jsonify({"status": "error", "message": "Entity not found"}), 404

    response = {
        "entity_id": entity_id,
        "current_state": state.get("current_state"),
        "data": state.get("data"),
        "last_updated": state.get("last_updated"),
    }
    return jsonify(response)


@app.route("/api/entity/<string:entity_id>/process", methods=["POST"])
@validate_request(ProcessDataRequest)
async def submit_data_for_processing(entity_id, data: ProcessDataRequest):
    job_id = f"proc-{datetime.utcnow().timestamp()}-{entity_id}"
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat() + "Z"}

    asyncio.create_task(process_data(job_id, entity_id, data.input_data))

    return jsonify({"status": "success", "message": "Processing started", "job_id": job_id})


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)