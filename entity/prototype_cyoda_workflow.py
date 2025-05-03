from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for job status and results
entity_job = {}

EXTERNAL_API_URL = "https://api.agify.io"

@dataclass
class InputData:
    name: str

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Workflow function for EntityJobResult
async def process_EntityJobResult(entity):
    """
    Workflow function that runs asynchronously before persistence.
    It performs the async processing, modifies entity state directly.
    """
    try:
        # Ensure requestedAt is set
        if "requestedAt" not in entity:
            entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"

        process_id = entity.get("processId")
        if not process_id:
            # Defensive: generate if missing
            process_id = str(uuid.uuid4())
            entity["processId"] = process_id

        # Defensive defaults for status/result
        if "status" not in entity:
            entity["status"] = "processing"
        if "result" not in entity:
            entity["result"] = None

        # Update in-memory cache immediately
        entity_job[process_id] = {
            "status": entity["status"],
            "requestedAt": entity["requestedAt"],
            "result": entity["result"]
        }

        name = entity.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("Entity missing or invalid required 'name' field")

        # Call external API asynchronously
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            api_data = response.json()

        # Build result dict with safe access
        result = {
            "name": name,
            "predicted_age": api_data.get("age"),
            "count": api_data.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Update entity state
        entity["status"] = "completed"
        entity["result"] = result

        # Update in-memory cache accordingly
        entity_job[process_id]["status"] = "completed"
        entity_job[process_id]["result"] = result

        # If needed, interact with other entities of different models here
        # e.g. await entity_service.add_item(token=cyoda_token, entity_model="OtherModel", entity_version=ENTITY_VERSION, entity={...})

    except Exception as e:
        entity["status"] = "failed"
        entity["result"] = None
        process_id = entity.get("processId", "unknown")
        entity_job[process_id] = {
            "status": "failed",
            "requestedAt": entity.get("requestedAt", ""),
            "result": None
        }
        logger.exception(f"Workflow process_EntityJobResult failed for processId={process_id}: {e}")

@app.route("/process-data", methods=["POST"])
@validate_request(InputData)
async def process_data(data: InputData):
    """
    Endpoint to start processing. Generates processId and calls update_item with workflow.
    """
    process_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    entity = {
        "processId": process_id,
        "name": data.name,
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
    }

    # Update in-memory cache immediately to allow quick GET
    entity_job[process_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
    }

    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="EntityJobResult",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=process_id,
            meta={},
            workflow=process_EntityJobResult
        )
    except Exception as e:
        logger.exception(f"Failed to create job entity with workflow for processId={process_id}: {e}")
        return jsonify({"error": "Failed to start processing"}), 500

    return jsonify({
        "processId": process_id,
        "status": "processing",
        "result": None
    }), 202

@app.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    """
    Endpoint to retrieve job results by process_id.
    Checks in-memory cache first, then fallback to entity service.
    """
    job = entity_job.get(process_id)
    if job:
        return jsonify({
            "processId": process_id,
            "status": job["status"],
            "result": job["result"]
        })

    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="EntityJobResult",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
        if not entity:
            return jsonify({"error": "processId not found"}), 404

        return jsonify({
            "processId": process_id,
            "status": entity.get("status", "unknown"),
            "result": entity.get("result")
        })
    except Exception as e:
        logger.exception(f"Failed to get job result from entity_service for processId={process_id}: {e}")
        return jsonify({"error": "internal error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)