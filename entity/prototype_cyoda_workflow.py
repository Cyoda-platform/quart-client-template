from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify
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

async def fetch_external_data():
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://icanhazdadjoke.com/", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("joke", "No joke found")

async def process_entity(process_id, input_data):
    try:
        logger.info(f"Processing job {process_id} with input: {input_data}")

        external_info = await fetch_external_data()

        result_data = {
            "inputReceived": input_data,
            "externalInfo": external_info,
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity={
                "status": "completed",
                "resultData": result_data,
                "completedAt": datetime.utcnow().isoformat() + "Z"
            },
            technical_id=process_id,
            meta={}
        )
        logger.info(f"Job {process_id} completed successfully")

    except Exception as e:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity={
                "status": "failed",
                "error": str(e),
                "completedAt": datetime.utcnow().isoformat() + "Z"
            },
            technical_id=process_id,
            meta={}
        )
        logger.exception(f"Job {process_id} failed during processing")

async def process_process_request(entity):
    # Mark as processing with timestamp
    entity.setdefault("status", "processing")
    entity.setdefault("createdAt", datetime.utcnow().isoformat() + "Z")
    # Generate and attach a correlation id for debugging/tracking
    entity["tempCorrelationId"] = str(uuid.uuid4())
    # Cannot launch background task here with final id since it's unknown before persistence
    # So just prepare entity state here
    return entity

@app.route('/process', methods=['POST'])
@validate_request(ProcessRequest)
async def process(data: ProcessRequest):
    input_data = data.inputData
    try:
        # Add item with workflow function which sets initial state
        process_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            entity=input_data,
            workflow=process_process_request
        )
        # Launch background async processing with known id
        asyncio.create_task(process_entity(process_id, input_data))
        return jsonify({
            "processId": process_id,
            "status": "processing"
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create process"}), 500

@app.route('/result/<string:process_id>', methods=['GET'])
async def get_result(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="process_request",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
        if not job:
            return jsonify({"error": "processId not found"}), 404
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

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)