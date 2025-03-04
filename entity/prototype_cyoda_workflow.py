#!/usr/bin/env python3
import asyncio
import logging
import uuid
import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
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

@dataclass
class ProcessRequest:
    # Using dict for nested data, TODO: adjust types if a more strict schema is needed
    inputData: dict  
    externalParams: dict  
    operation: str

@app.route('/process', methods=['POST'])
@validate_request(ProcessRequest)  # POST: validation goes second due to library workaround issues.
async def process(data: ProcessRequest):
    try:
        process_data = {
            "inputData": data.inputData,
            "externalParams": data.externalParams,
            "operation": data.operation,
        }
        # Prepare the job data to be stored externally.
        job_data = {
            "status": "processing",
            "requestedAt": datetime.datetime.utcnow().isoformat(),
            "inputData": process_data.get("inputData"),
            "externalParams": process_data.get("externalParams"),
            "operation": process_data.get("operation"),
        }
        # Call add_item with workflow function that will process the entity asynchronously before persistence.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,  # the validated data object
            workflow=process_entity_job  # Workflow function that processes the entity data
        )
        logger.info(f"Received process request for {new_id}")
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
        # Return current entity state
        if job.get("status") != "completed":
            return jsonify({"status": job.get("status"), "result": "Processing not complete"}), 200
        
        return jsonify({
            "status": "found",
            "result": job.get("result")
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# Workflow function for entity_job.
# This function is invoked asynchronously before the current entity is persisted.
# It moves all processing logic that was originally in separate async tasks.
async def process_entity_job(entity):
    try:
        # Using entity's "externalParams" to call an external API.
        async with httpx.AsyncClient() as client:
            external_url = "https://example.com/api"  # Replace with actual external API URL as needed.
            external_params = entity.get("externalParams", {})
            external_response = await client.post(external_url, json=external_params)
            external_data = external_response.json()
            logger.info(f"Received external data for entity_job: {external_data}")
        
        # Process business logic based on "operation".
        operation = entity.get("operation")
        input_data = entity.get("inputData", {})
        if operation == "calculate_discount":
            # Example: apply a 10% discount.
            value = input_data.get("value", 0)
            result = {
                "id": input_data.get("id"),
                "calculation": value * 0.9,
                "details": "Discount applied."
            }
        else:
            result = {
                "id": input_data.get("id"),
                "calculation": None,
                "details": f"Operation '{operation}' not supported."
            }
        
        # Simulate processing delay if necessary.
        await asyncio.sleep(1)
        # Modify the entity state directly.
        entity["status"] = "completed"
        entity["result"] = result
        entity["completedAt"] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
        # Directly modify the entity state in case of errors.
        entity["status"] = "error"
        entity["error"] = str(e)
    return entity

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)