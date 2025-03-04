from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
import datetime
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import httpx

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for documentation support

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class ProcessRequest:
    # Using dict for nested data; adjust types as needed
    inputData: dict  
    externalParams: dict  
    operation: str

@app.route('/process', methods=['POST'])
@validate_request(ProcessRequest)
async def process(data: ProcessRequest):
    try:
        process_data = {
            "inputData": data.inputData,
            "externalParams": data.externalParams,
            "operation": data.operation,
        }
        # Prepare the job data with initial state. This entity will be passed to the workflow function.
        job_data = {
            "status": "processing",
            "requestedAt": datetime.datetime.utcnow().isoformat(),
            "inputData": process_data.get("inputData"),
            "externalParams": process_data.get("externalParams"),
            "operation": process_data.get("operation"),
        }
        # Call add_item with workflow function that processes the entity asynchronously before persistence.
        # The workflow function will modify the entity directly.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # validated job data
            )
        logger.info(f"Received process request. Assigned ID: {new_id}")
        return jsonify({
            "status": "success",
            "message": "Processing initiated.",
            "processedId": new_id
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/results/<processed_id>', methods=['GET'])
async def get_results(processed_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=processed_id
        )
        if not job:
            return jsonify({"status": "not_found", "result": None}), 404
        
        # Return current entity state; if still processing or in error, it will indicate so.
        if job.get("status") != "completed":
            return jsonify({"status": job.get("status"), "result": "Processing not complete"}), 200
        
        return jsonify({
            "status": "found",
            "result": job.get("result")
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)