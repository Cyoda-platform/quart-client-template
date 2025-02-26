from common.grpc_client.grpc_client import grpc_stream
import asyncio
from datetime import datetime

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# External API configuration
EXTERNAL_API_URL = "https://services.cro.ie/cws/companies"
AUTHORIZATION_HEADER = "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"

# Data model for request validation
class ExternalDataRequest:
    company_name: str
    skip: int
    max: int

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route("/external-data", methods=["POST"])
@validate_request(ExternalDataRequest)
async def external_data(data: ExternalDataRequest):
    # Create a job record with initial status and store external request parameters.
    job = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "data": None,
        "params": data.__dict__  # Save parameters for workflow processing.
    }
    # Persist the job record with the workflow function applied.
    # The workflow function will execute asynchronously before the entity is persisted.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="external_data",
        entity_version=ENTITY_VERSION,
        entity=job,
        )
    return jsonify({"status": "processing", "job_id": job_id})

@app.route("/results", methods=["GET"])
async def get_results():
    # Retrieve job records from storage.
    try:
        results = await entity_service.get_items(
            token=cyoda_token,
            entity_model="external_data",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "success", "results": results})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)