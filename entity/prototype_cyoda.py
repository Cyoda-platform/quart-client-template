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

async def process_entity(job, payload):
    # Fetch data from external API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as response:
                data = await response.json()
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        return

    # Instead of storing in a local cache, add the item using the external service.
    # This call returns an id which can later be retrieved via a separate GET endpoint.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data  # the validated data object
    )
    job["status"] = "completed"
    job["completedAt"] = datetime.datetime.utcnow().isoformat()
    job["entity_id"] = new_id

# Workaround for quart-schema issue:
# For POST requests, the route decorator must be first, followed by the validation decorator.
@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(BrandFetchInput)  # Placed after route for POST requests - WORKAROUND for quart-schema issue.
async def fetch_brands(data: BrandFetchInput):
    # Create a job record to track the processing status.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task to fetch external API data and store it via entity_service.
    asyncio.create_task(process_entity(JOBS[job_id], data.__dict__))

    # Return a response indicating that the data fetch was scheduled.
    # The actual entity data can be retrieved later via GET /api/brands endpoint.
    response = {
        "status": "success",
        "message": "Data fetch scheduled. Retrieve stored entity via GET /api/brands once processing is complete.",
        "job_id": job_id
    }
    return jsonify(response), 200

# GET endpoint to retrieve stored entities via external service.
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