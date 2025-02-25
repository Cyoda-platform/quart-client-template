#!/usr/bin/env python3
"""
prototype.py
A working prototype for fetching and serving brand data using Quart, aiohttp, and quart‑schema.
This prototype demonstrates the basic UX and identifies potential gaps before a full implementation.
"""

import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # Note: For GET requests, validation is applied before @app.route.
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

@dataclass
class FetchBrandsRequest:
    filter: str  # TODO: Currently not used, optional filter parameter

async def process_entity(job_id):
    """
    Asynchronous background task to fetch brand data from the external API,
    process it, store the data via the external entity_service, and update the job status.
    """
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    headers = {"accept": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Update the "brands" entity in the external service.
                    existing_brands = await entity_service.get_items(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                    )
                    if existing_brands:
                        await entity_service.update_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=data,
                            meta={}
                        )
                    else:
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=data
                        )
                    # Update the job status to completed.
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="jobs",
                        entity_version=ENTITY_VERSION,
                        entity={"technical_id": job_id, "status": "completed"},
                        meta={}
                    )
                else:
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="jobs",
                        entity_version=ENTITY_VERSION,
                        entity={"technical_id": job_id, "status": "failed"},
                        meta={}
                    )
    except Exception as e:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="jobs",
            entity_version=ENTITY_VERSION,
            entity={"technical_id": job_id, "status": "failed"},
            meta={}
        )
        # Log the error appropriately.
        print(f"Error processing job {job_id}: {e}")

@app.route("/api/brands/fetch", methods=["POST"])
@validate_request(FetchBrandsRequest)  # Workaround: For POST endpoints, place validate_request after route decoration.
async def fetch_brands(data: FetchBrandsRequest):
    """
    POST endpoint to trigger fetching of brand data from the external API.
    This endpoint starts an asynchronous background task to process the data.
    It adds a job record via the external entity_service and returns the job identifier.
    """
    job_data = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Create a job entry in the external service.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="jobs",
        entity_version=ENTITY_VERSION,
        entity=job_data
    )
    # Fire-and-forget the processing task.
    asyncio.create_task(process_entity(job_id))
    # Return immediate response; processed data will be available via the GET endpoint.
    return jsonify({
        "status": "success",
        "job_id": job_id,
        "message": "Data fetch initiated."
    })

@app.route("/api/brands", methods=["GET"])
async def get_brands():
    """
    GET endpoint to return the cached brand data stored via the external service.
    If no data is available, informs the user accordingly.
    """
    brands = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if brands:
        # Assuming that the stored brands record is the first entry.
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