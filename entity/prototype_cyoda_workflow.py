#!/usr/bin/env python3
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

# Data class for POST /api/brands/fetch request.
@dataclass
class BrandFetchInput:
    trigger: bool

# In-memory storage for job status tracking.
JOBS = {}  # job_id -> {status, requestedAt, completedAt, entity_id, error?}

# Workflow function applied to the "brands" entity before persistence.
# This function fetches external data, updates the entity state and adds metadata.
async def process_brands(entity):
    # Validate the entity input minimally
    if "trigger" not in entity or not entity["trigger"]:
        entity["error"] = "Trigger flag is missing or false."
        entity["processed_at"] = datetime.datetime.utcnow().isoformat()
        return entity

    try:
        async with aiohttp.ClientSession() as session:
            # Attempt to fetch external brand data
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as response:
                # Check if response status is OK
                if response.status != 200:
                    entity["error"] = f"External API returned status {response.status}."
                    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
                    return entity
                fetched_data = await response.json()
    except Exception as e:
        # If an exception occurs during fetch, record error in entity.
        entity["error"] = f"Exception during external API fetch: {str(e)}"
        entity["processed_at"] = datetime.datetime.utcnow().isoformat()
        return entity

    # Update the entity with fetched data and processing metadata.
    entity["data"] = fetched_data
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

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
            workflow=process_brands  # asynchronous workflow to modify entity before persistence
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