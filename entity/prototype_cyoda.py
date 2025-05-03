from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence for process jobs
entity_job = {}

# Example external API: https://api.agify.io/?name=michael (predicts age by name)
EXTERNAL_API_URL = "https://api.agify.io"

@dataclass
class InputData:
    name: str  # primitive type as per requirements

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def process_entity(entity_job, process_id, input_data):
    try:
        name = input_data.name
        async with httpx.AsyncClient() as client:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            api_data = response.json()

        result = {
            "name": name,
            "predicted_age": api_data.get("age"),
            "count": api_data.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Update the job status and result in in-memory cache
        entity_job[process_id]["status"] = "completed"
        entity_job[process_id]["result"] = result
        logger.info(f"Processing completed for processId={process_id}")

        # Save the result to entity_service asynchronously (fire and forget)
        try:
            # Use the process_id as technical_id, save result as entity data
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="EntityJobResult",
                entity_version=ENTITY_VERSION,
                entity=result,
                technical_id=process_id,
                meta={}
            )
        except Exception as e:
            logger.exception(f"Failed to save result to entity_service for processId={process_id}: {e}")

    except Exception as e:
        entity_job[process_id]["status"] = "failed"
        entity_job[process_id]["result"] = None
        logger.exception(f"Error processing processId={process_id}: {e}")

# POST endpoint: validation last due to quart-schema library issue workaround
@app.route("/process-data", methods=["POST"])
@validate_request(InputData)
async def process_data(data: InputData):
    process_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[process_id] = {"status": "processing", "requestedAt": requested_at, "result": None}

    # Add new job entry to entity_service, just store the empty job meta, id is process_id
    try:
        # We add item and get an id, but we want to use our generated process_id as technical_id
        # Since add_item returns new id, and we want to keep process_id, we skip add_item and rely on update_item instead
        # So we just create empty placeholder by update_item with process_id as technical_id
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="EntityJobResult",
            entity_version=ENTITY_VERSION,
            entity={"status": "processing", "requestedAt": requested_at, "result": None},
            technical_id=process_id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Failed to create job entry in entity_service for processId={process_id}: {e}")

    asyncio.create_task(process_entity(entity_job, process_id, data))

    return jsonify({
        "processId": process_id,
        "status": "processing",
        "result": None
    }), 202

# GET endpoint: validation first due to quart-schema library issue workaround
@app.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    # Try to get from local cache first
    job = entity_job.get(process_id)
    if job:
        return jsonify({
            "processId": process_id,
            "status": job["status"],
            "result": job["result"]
        })

    # If not found locally, try to get from entity_service
    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="EntityJobResult",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
        if not entity:
            return jsonify({"error": "processId not found"}), 404

        # Map entity data to response format
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