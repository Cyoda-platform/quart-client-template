from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
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

@dataclass
class ProcessRequest:
    inputData: dict

@app.route('/process', methods=['POST'])
@validate_request(ProcessRequest)
async def process(data: ProcessRequest):
    input_data = data.inputData

    try:
        # Add item to external entity_service
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity=input_data
        )
        # Return id only, no immediate retrieval of result
        return jsonify({
            "processId": id,
            "status": "processing"
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create process"}), 500

@app.route('/result/<string:process_id>', methods=['GET'])
async def get_result(process_id):
    try:
        # Retrieve the item by id
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
        if not job:
            return jsonify({"error": "processId not found"}), 404

        # The job dict should contain status, resultData, error, etc.
        response = {
            "processId": process_id,
            "status": job.get("status", "unknown"),
            "resultData": job.get("resultData")
        }
        if job.get("status") == "failed":
            response["error"] = job.get("error")

        return jsonify(response)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve process result"}), 500

async def fetch_external_data():
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get("https://icanhazdadjoke.com/", headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("joke", "No joke found")
        except Exception as e:
            logger.exception("Failed to fetch external data")
            raise e

# Background task to process entity and update external store
async def process_entity(job_id, input_data):
    try:
        logger.info(f"Processing job {job_id} with input: {input_data}")

        external_info = await fetch_external_data()

        result_data = {
            "inputReceived": input_data,
            "externalInfo": external_info,
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }

        # Update entity_service with result data and status completed
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity={
                "status": "completed",
                "resultData": result_data,
                "completedAt": datetime.utcnow().isoformat() + "Z"
            },
            technical_id=job_id,
            meta={}
        )

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        # Update entity_service with failure status and error message
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity={
                "status": "failed",
                "error": str(e),
                "completedAt": datetime.utcnow().isoformat() + "Z"
            },
            technical_id=job_id,
            meta={}
        )
        logger.exception(f"Job {job_id} failed during processing")

@app.before_serving
async def startup():
    # There is no in-memory entity_jobs anymore, so no background tasks running on startup
    pass

# Overriding the background task creation to use external entity_service
@app.route('/process', methods=['POST'])
@validate_request(ProcessRequest)
async def process(data: ProcessRequest):
    input_data = data.inputData

    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity=input_data
        )
        # launch background task to process and update entity_service
        asyncio.create_task(process_entity(id, input_data))

        return jsonify({
            "processId": id,
            "status": "processing"
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create process"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)