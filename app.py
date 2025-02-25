from common.grpc_client.grpc_client import grpc_stream
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, jsonify
import aiohttp
from quart_schema import QuartSchema, validate_request

# Import external entity service functions and required constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema for the app

# Startup initialization for cyoda external service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Data class for POST /api/brands/fetch request.
@dataclass
class BrandFetchInput:
    trigger: bool

# In-memory storage for job status tracking.
JOBS = {}  # job_id -> {status, requestedAt, completedAt, entity_id, error?}

# Endpoint to trigger data fetch and processing.
# The heavy asynchronous logic is moved into the workflow function.
@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(BrandFetchInput)  # WORKAROUND for quart-schema ordering
async def fetch_brands(data: BrandFetchInput):
    # Create a job record to track processing status.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Prepare the initial entity with minimal information.
    initial_entity = {
        "trigger": data.trigger,
        "requestedAt": requested_at,
    }

    try:
        # When adding the item, the workflow process_brands is invoked asynchronously
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=initial_entity,  # initial entity state
            )
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()
        JOBS[job_id]["entity_id"] = new_id
    except Exception as e:
        # Capture any error during the persistence process.
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = f"Error during entity add: {str(e)}"
        return jsonify({
            "status": "failed",
            "message": "An error occurred during processing.",
            "job_id": job_id
        }), 500

    # Return response indicating that processing has been scheduled and completed.
    response = {
        "status": "success",
        "message": "Data fetch and processing completed. Retrieve stored entity via GET /api/brands.",
        "job_id": job_id,
        "entity_id": new_id,
    }
    return jsonify(response), 200

# GET endpoint to retrieve stored brand entities via external service.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve stored brand data using the external entity service.
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({
            "status": "failed",
            "message": f"Error retrieving items: {str(e)}"
        }), 500

    return jsonify(items), 200

if __name__ == '__main__':
    # Run the Quart application.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)