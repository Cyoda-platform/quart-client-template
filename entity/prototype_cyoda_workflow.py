#!/usr/bin/env python3
import asyncio
import datetime
import uuid
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    # Initialize external service
    await init_cyoda(cyoda_token)

@dataclass
class FetchBrandsRequest:
    force_refresh: bool = False

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    # Generate a unique job id and current timestamp
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Create initial job record state
    job_record = {
        "job_id": job_id,
        "requestedAt": requested_at,
        "status": "processing",
        "brands": []
    }
    # Create job record through entity_service and apply workflow function before persistence.
    created_job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="jobs",
        entity_version=ENTITY_VERSION,
        entity=job_record,
        workflow=process_job_workflow  # Workflow function to process the job record asynchronously.
    )
    # Simply return the job id.
    return jsonify({
        "status": "success",
        "message": "Brands fetch job started.",
        "job_id": created_job_id
    })

# Workflow function applied to the job entity before persistence.
# This function handles fetching brands data from external API,
# updates the job entity state and also updates a supplementary brands entity.
async def process_job_workflow(job_entity):
    url = "https://api.practicesoftwaretesting.com/brands"
    try:
        # Create an HTTP session to fetch brands data.
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"accept": "application/json"}, timeout=10) as resp:
                # If the external service returns a successful response, process the data.
                if resp.status == 200:
                    brands_data = await resp.json()
                    job_entity["status"] = "completed"
                    job_entity["brands"] = brands_data
                    # Update supplementary brands entity.
                    try:
                        await entity_service.update_item(
                            token=cyoda_token,
                            entity_model="brands",  # different entity_model from jobs.
                            entity_version=ENTITY_VERSION,
                            entity={"data": brands_data},
                            meta={}
                        )
                    except Exception:
                        # Log or handle supplementary update error if needed.
                        pass
                else:
                    # Non-200 response marks the job as error.
                    job_entity["status"] = "error"
    except Exception:
        # Handle exceptions related to network or data processing.
        job_entity["status"] = "error"
    # Add a timestamp indicating when the workflow was applied.
    job_entity["workflow_applied_at"] = datetime.datetime.utcnow().isoformat()
    return job_entity

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve brands cache from external service.
    try:
        brands_items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
    except Exception:
        # In case of retrieval error, return empty list with error status.
        return jsonify({
            "status": "error",
            "data": []
        })
    return jsonify({
        "status": "success",
        "data": brands_items
    })

if __name__ == '__main__':
    # Run the Quart application.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)