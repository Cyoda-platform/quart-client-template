import asyncio
import logging
import uuid
import datetime

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for documentation support

# In-memory store for processed entities (mock persistence)
entity_jobs = {}

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
        await asyncio.sleep(1)  # TODO: Adjust or remove in production
        
        # Update the in-memory store with the processed result
        entity_jobs[processed_id]["status"] = "completed"
        entity_jobs[processed_id]["result"] = result
        entity_jobs[processed_id]["completedAt"] = datetime.datetime.utcnow().isoformat()
        logger.info(f"Processing completed for {processed_id}")
    except Exception as e:
        logger.exception(e)
        entity_jobs[processed_id]["status"] = "error"
        entity_jobs[processed_id]["error"] = str(e)

@app.route('/process', methods=['POST'])
async def process():
    try:
        process_data = await request.get_json()
        if not process_data:
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        processed_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()
        entity_jobs[processed_id] = {
            "status": "processing",
            "requestedAt": requested_at
        }
        
        logger.info(f"Received process request for {processed_id}")
        
        # Fire and forget the background processing task
        asyncio.create_task(process_entity(processed_id, process_data))
        
        return jsonify({
            "status": "success",
            "message": "Processing initiated.",
            "processedId": processed_id
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/results/<processed_id>', methods=['GET'])
async def get_results(processed_id):
    try:
        job = entity_jobs.get(processed_id)
        if not job:
            return jsonify({"status": "not_found", "result": None}), 404
        # If processing is still in progress or encountered an error, return that status.
        if job["status"] != "completed":
            return jsonify({"status": job["status"], "result": "Processing not complete"}), 200
        
        return jsonify({
            "status": "found",
            "result": job.get("result")
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)