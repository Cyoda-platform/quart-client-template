from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Dataclass for POST /process request validation
@dataclass
class ProcessRequest:
    inputData: dict  # TODO: refine structure if needed

async def call_external_api(input_value: str) -> dict:
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
    try:
        name = input_data.get("name")
        if not name:
            raise ValueError("Missing 'name' in inputData")
        result = await call_external_api(name)
        processed_result = {
            "inputName": name,
            "predictedAge": result.get("age"),
            "count": result.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }
        # Use entity_service to update the job entity with results
        # First retrieve the job data
        job_data = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_jobs",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job_data:
            logger.error(f"Job ID {job_id} not found in entity service during processing")
            return
        job_data["status"] = "completed"
        job_data["result"] = processed_result
        job_data["completedAt"] = datetime.utcnow().isoformat() + "Z"
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_jobs",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            technical_id=job_id,
            meta={}
        )
    except Exception as e:
        logger.exception(f"Processing failed for job {job_id}: {e}")
        try:
            job_data = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="entity_jobs",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
            if job_data:
                job_data["status"] = "failed"
                job_data["message"] = str(e)
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="entity_jobs",
                    entity_version=ENTITY_VERSION,
                    entity=job_data,
                    technical_id=job_id,
                    meta={}
                )
        except Exception as e2:
            logger.exception(f"Failed to update failure status for job {job_id}: {e2}")

@app.route("/process", methods=["POST"])
# NOTE: validate_request placed after route decorator due to quart-schema defect workaround
@validate_request(ProcessRequest)
async def post_process(data: ProcessRequest):
    try:
        input_data = data.inputData
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"
        job_entity = {
            "status": "processing",
            "requestedAt": requested_at,
            "inputData": input_data
        }
        # Add job entity to entity_service
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_jobs",
            entity_version=ENTITY_VERSION,
            entity={"id": job_id, **job_entity}  # include id in entity data as technical_id is separate
        )
        asyncio.create_task(process_entity(job_id, input_data))
        return jsonify({"processId": job_id, "status": "processing", "message": "Processing started"}), 202
    except Exception as e:
        logger.exception(f"Error in /process endpoint: {e}")
        return jsonify({"message": "Invalid request or internal error"}), 500

@app.route("/result/<process_id>", methods=["GET"])
async def get_result(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_jobs",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
        if not job:
            return jsonify({"message": f"Process ID {process_id} not found"}), 404
        response = {"processId": process_id, "status": job.get("status"), "message": job.get("message", "")}
        if job.get("status") == "completed":
            response["result"] = job.get("result")
        return jsonify(response), 200
    except Exception as e:
        logger.exception(f"Error retrieving result for process ID {process_id}: {e}")
        return jsonify({"message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)