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
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data  # the validated data object
        )
        logger.info(f"Received process request for {new_id}")
        # Fire and forget the background processing task.
        asyncio.create_task(process_entity(new_id, process_data))
        
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
        # If processing is still in progress or encountered an error, return that status.
        if job.get("status") != "completed":
            return jsonify({"status": job.get("status"), "result": "Processing not complete"}), 200
        
        return jsonify({
            "status": "found",
            "result": job.get("result")
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

async def process_entity(processed_id, process_data):
    """
    Background task to process the entity.
    process_data is expected to have:
      - "inputData": dict with necessary data
      - "externalParams": dict with parameters for external API call
      - "operation": string to decide business logic (e.g. "calculate_discount")
    
    Uses httpx.AsyncClient to invoke an external API as a POST, and then performs
    business logic calculations.
    """
    try:
        logger.info(f"Starting processing for {processed_id}")
        
        # Simulate external API call using httpx.AsyncClient
        async with httpx.AsyncClient() as client:
            # TODO: Replace URL and parameters with actual external API details
            external_url = "https://example.com/api"
            external_params = process_data.get("externalParams", {})
            external_response = await client.post(external_url, json=external_params)
            external_data = external_response.json()
            # TODO: Handle external_data properly as per business requirements.
            logger.info(f"Received external data for {processed_id}: {external_data}")
        
        # Apply business logic and calculation based on the specified operation
        operation = process_data.get("operation")
        input_data = process_data.get("inputData", {})
        result = {}

        if operation == "calculate_discount":
            # Example calculation: apply a 10% discount
            value = input_data.get("value", 0)
            result = {
                "id": input_data.get("id"),
                "calculation": value * 0.9,  # discount calculation
                "details": "Discount applied."
            }
        else:
            # TODO: Implement additional operations as necessary
            result = {
                "id": input_data.get("id"),
                "calculation": None,
                "details": f"Operation '{operation}' not supported."
            }
        
        # Simulate processing delay
        await asyncio.sleep(1)  # TODO: Adjust or remove this delay in production
        
        updated_data = {
            "status": "completed",
            "result": result,
            "completedAt": datetime.datetime.utcnow().isoformat()
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=updated_data,
            technical_id=processed_id,
            meta={}
        )
        logger.info(f"Processing completed for {processed_id}")
    except Exception as e:
        logger.exception(e)
        error_data = {
            "status": "error",
            "error": str(e)
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=error_data,
                technical_id=processed_id,
                meta={}
            )
        except Exception as inner_e:
            logger.exception(inner_e)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)