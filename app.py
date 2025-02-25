from common.grpc_client.grpc_client import grpc_stream
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

# Startup initialization for cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class FetchBrandsRequest:
    filter: str  # TODO: Currently not used, optional filter parameter

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