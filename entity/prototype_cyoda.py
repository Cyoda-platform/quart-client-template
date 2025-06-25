from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

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
class ProcessData:
    name: str

# In-memory local cache for workflow states and results.
# Structure: {workflowId: {"status": str, "requestedAt": datetime, "result": dict or None}}
entity_jobs = {}

# Example real external API to fetch some data for demonstration:
EXTERNAL_API_URL = "https://api.agify.io"

async def fetch_external_data(name: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            data = response.json()
            logger.info(f"External API data fetched for name={name}: {data}")
            return data
        except httpx.HTTPError as e:
            logger.exception(f"External API request failed: {e}")
            return {"error": "Failed to fetch external data"}

async def process_entity(entity_jobs_cache: dict, workflow_id: str, input_data: dict):
    try:
        name = input_data.get("name", "unknown")
        external_data = await fetch_external_data(name)
        result = {
            "inputName": name,
            "predictedAge": external_data.get("age"),
            "count": external_data.get("count"),
            "source": "agify.io"
        }
        await asyncio.sleep(2)
        entity_jobs_cache[workflow_id]["status"] = "completed"
        entity_jobs_cache[workflow_id]["result"] = result
        logger.info(f"Workflow {workflow_id} completed with result: {result}")
    except Exception as e:
        logger.exception(f"Error processing workflow {workflow_id}: {e}")
        entity_jobs_cache[workflow_id]["status"] = "failed"
        entity_jobs_cache[workflow_id]["result"] = {"error": str(e)}

@app.route("/process-data", methods=["POST"])
@validate_request(ProcessData)  # Workaround: validation for POST placed after route decorator due to quart-schema defect
async def process_data(data: ProcessData):
    try:
        # Prepare data dict for entity_service
        data_dict = data.__dict__
        # Add item via entity_service, entity_model is 'process_data' (underscore lowercase entity name)
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="process_data",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        # Return only id, cannot immediately retrieve result, separate endpoint needed
        return jsonify({"id": str(id)}), 202
    except Exception as e:
        logger.exception(f"Failed to start processing: {e}")
        return jsonify({"error": "Failed to start processing"}), 500

@app.route("/results/<string:workflow_id>", methods=["GET"])
async def get_results(workflow_id: str):
    # Retrieve item by id from entity_service where entity_model = 'process_data'
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="process_data",
            entity_version=ENTITY_VERSION,
            technical_id=workflow_id
        )
        if not item:
            return jsonify({"error": "Workflow ID not found"}), 404
        # item expected to have keys: status, result, requestedAt or similar if stored
        response = {
            "workflowId": workflow_id,
            "status": item.get("status", "unknown"),
            "result": item.get("result", None),
        }
        return jsonify(response), 200
    except Exception as e:
        logger.exception(f"Error retrieving results for workflow {workflow_id}: {e}")
        return jsonify({"error": "Error retrieving results"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)