#!/usr/bin/env python3
"""
prototype.py
A working prototype for fetching and serving brand data using Quart, aiohttp, and quart‐schema.
This refactored application moves background and processing logic into workflow functions,
making the controllers lean and ensuring that asynchronous tasks are invoked via workflow functions.
"""

import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # For GET endpoints, validation is applied prior to @app.route.
import aiohttp

# Import external service and configuration constants
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Workflow function for processing job entities before persistence.
# This function is invoked before the job entity is stored.
# It initiates the asynchronous task to fetch and process brand data.
async def process_jobs(job: dict) -> dict:
    # Ensure a unique technical_id exists for the job.
    if "technical_id" not in job or not job["technical_id"]:
        job["technical_id"] = str(uuid.uuid4())
    # Launch the asynchronous background task using fire-and-forget pattern.
    try:
        # Wrap in try/except to ensure any exception is caught
        asyncio.create_task(process_entity(job["technical_id"]))
    except Exception as e:
        # If task initiation fails, mark the job as failed.
        job["status"] = "failed"
        print(f"Failed to initiate background process for job {job['technical_id']}: {e}")
    # Add workflow processing metadata.
    job["workflowProcessedAt"] = datetime.utcnow().isoformat()
    return job

# Workflow function for processing brands entities before persistence.
# This function can add supplementary attributes or perform additional transformations.
async def process_brands(entity: dict) -> dict:
    # Mark the brand data as processed and add processing timestamp.
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat()
    # Here you can perform additional transformations or add supplementary data.
    return entity

# Startup initialization for cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class FetchBrandsRequest:
    filter: str  # TODO: Currently not used, optional filter parameter

# This asynchronous function runs in background.
# It fetches the external brands data and updates the brands entity accordingly.
async def process_entity(job_id: str):
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    headers = {"accept": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check if there is an existing brands entity.
                    existing_brands = await entity_service.get_items(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                    )
                    if existing_brands:
                        # If brands entity exists, update it.
                        await entity_service.update_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=data,
                            meta={}
                        )
                    else:
                        # If no brands entity exists, add a new one applying the workflow.
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=data,
                            workflow=process_brands  # Apply workflow function before persisting.
                        )
                    # Update the corresponding job status to completed.
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="jobs",
                        entity_version=ENTITY_VERSION,
                        entity={"technical_id": job_id, "status": "completed"},
                        meta={}
                    )
                else:
                    # On non-200 response update job as failed.
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="jobs",
                        entity_version=ENTITY_VERSION,
                        entity={"technical_id": job_id, "status": "failed"},
                        meta={}
                    )
    except Exception as e:
        # On exception, update job as failed and log error.
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="jobs",
            entity_version=ENTITY_VERSION,
            entity={"technical_id": job_id, "status": "failed"},
            meta={}
        )
        print(f"Error processing job {job_id}: {e}")

@app.route("/api/brands/fetch", methods=["POST"])
@validate_request(FetchBrandsRequest)  # For POST endpoints, validation is applied after route decoration.
async def fetch_brands(data: FetchBrandsRequest):
    """
    POST endpoint to trigger fetching of brand data from the external API.
    This endpoint creates a new job entity via entity_service.
    The workflow function (process_jobs) is applied asynchronously before persistence,
    which in turn starts the background task for data processing.
    """
    job_data = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Add a job entity with the workflow function to trigger background processing.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="jobs",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_jobs  # Workflow function that triggers background processing.
    )
    return jsonify({
        "status": "success",
        "job_id": job_id,
        "message": "Data fetch initiated."
    })

@app.route("/api/brands", methods=["GET"])
async def get_brands():
    """
    GET endpoint to return cached brand data from the external service.
    If no data is available, informs the user accordingly.
    """
    brands = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if brands:
        # Assuming the stored brands record is the first entry.
        return jsonify({
            "status": "success",
            "data": brands[0]
        })
    else:
        return jsonify({
            "status": "pending",
            "message": "Brand data is not yet available. Please try again shortly."
        })

if __name__ == "__main__":
    app.run(
        use_reloader=False,
        debug=True,
        host="0.0.0.0",
        port=8000,
        threaded=True
    )