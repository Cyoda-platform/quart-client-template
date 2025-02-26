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
    await init_cyoda(cyoda_token)

@dataclass
class FetchBrandsRequest:
    force_refresh: bool = False

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    # Generate a job id and requested time
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Create a job record with initial state.
    job_record = {
        "job_id": job_id,
        "requestedAt": requested_at,
        "status": "processing",
        "brands": []
    }
    # The workflow function will fetch brands and update the job record before persistence.
    created_job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="jobs",
        entity_version=ENTITY_VERSION,
        entity=job_record,
        workflow=process_job_workflow  # Workflow function to process job data.
    )

    # Simply return the job id.
    return jsonify({
        "status": "success",
        "message": "Brands fetch job started.",
        "job_id": created_job_id
    })

# Workflow function applied to the job entity before persistence.
# This workflow function asynchronously fetches brands data and updates the job entity state.
async def process_job_workflow(job_entity):
    url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    brands_data = await resp.json()
                    # Update job entity state to 'completed' and add brands data.
                    job_entity["status"] = "completed"
                    job_entity["brands"] = brands_data
                    # Update supplementary brands entity (different entity_model).
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity={"data": brands_data},
                        meta={}
                    )
                else:
                    job_entity["status"] = "error"
    except Exception:
        job_entity["status"] = "error"
    # Optionally add a workflow timestamp.
    job_entity["workflow_applied_at"] = datetime.datetime.utcnow().isoformat()
    return job_entity

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve the brands cache from the external service.
    brands_items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION
    )
    return jsonify({
        "status": "success",
        "data": brands_items
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)