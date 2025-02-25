#!/usr/bin/env python3
import asyncio
import uuid
import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
import aiohttp
from quart_schema import QuartSchema, validate_request

# Import external entity service functions and required constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema for the app

# Startup initialization for cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data class for POST /api/brands/fetch request, expects {"trigger": true}
@dataclass
class BrandFetchInput:
    trigger: bool

# Local in‑memory storage for job status tracking (preserved business logic)
JOBS = {}  # Store job status and metadata

# Workflow function applied to the "brands" entity before persistence.
# It is executed asynchronously by entity_service.add_item.
# This function takes the entity (a dict) as the only argument,
# and can modify its state before it is persisted.
async def process_brands(entity):
    # Fetch external API data and update the entity with the fetched data.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as response:
                fetched_data = await response.json()
        # Modify the entity with external data and additional metadata.
        entity["data"] = fetched_data
        entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        # Since we cannot add/update the current entity using service calls,
        # we flag the error directly in the entity state.
        entity["error"] = str(e)
    return entity

# Endpoint to trigger data fetch and processing.
# The excessive asynchronous logic is moved to the workflow function.
@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(BrandFetchInput)  # WORKAROUND for quart-schema issue: decorator order matters.
async def fetch_brands(data: BrandFetchInput):
    # Create a job record to track the processing status.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Prepare the initial entity. Minimal data from the client is recorded.
    # All heavy lifting (i.e. external data fetch and modifications) will be done in process_brands.
    initial_entity = {
        "trigger": data.trigger,
        "requestedAt": requested_at,
    }

    # Add the item using the external service.
    # The workflow function process_brands will be invoked asynchronously before persisting.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=initial_entity,  # initial entity data
        workflow=process_brands  # asynchronous workflow function to modify the entity before persistence
    )
    JOBS[job_id]["status"] = "completed"
    JOBS[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()
    JOBS[job_id]["entity_id"] = new_id

    # Return a response indicating that the process was scheduled.
    response = {
        "status": "success",
        "message": "Data fetch scheduled. Retrieve stored entity via GET /api/brands once processing is complete.",
        "job_id": job_id,
        "entity_id": new_id,
    }
    return jsonify(response), 200

# GET endpoint to retrieve stored entities via the external service.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # Retrieve the stored brand data using the external service.
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(items), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)