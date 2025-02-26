#!/usr/bin/env python3
import asyncio
import datetime
import uuid
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
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
    # In this refactored implementation we replace in‐memory cache with external service calls.
    force_refresh = data.force_refresh  # Not used in this prototype, but available for potential caching logic.
    
    # Generate a job id and requested time
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    
    # Create a job record in the external service. The returned technical id is used later.
    job_record = {
        "job_id": job_id,
        "requestedAt": requested_at,
        "status": "processing",
        "brands": []
    }
    # Add workflow function to be applied asynchronously before persistence.
    created_job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="jobs",
        entity_version=ENTITY_VERSION,
        entity=job_record,
        workflow=process_jobs  # Workflow function applied to the job record.
    )
    
    # Fire and forget the processing task.
    asyncio.create_task(process_brands_fetch(created_job_id, requested_at))
    
    # Return only the job id in the response.
    return jsonify({
        "status": "success",
        "message": "Brands fetch job started.",
        "job_id": created_job_id
    })

# Workflow function applied to the job entity before persistence.
async def process_jobs(job_entity):
    # For example add a workflow timestamp.
    job_entity["workflow_applied_at"] = datetime.datetime.utcnow().isoformat()
    return job_entity

async def process_brands_fetch(job_id, requested_at):
    url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    brands_data = await resp.json()
                    # Update the externally stored job record to indicate completion.
                    completed_job = {
                        "job_id": job_id,
                        "requestedAt": requested_at,
                        "status": "completed",
                        "brands": brands_data
                    }
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="jobs",
                        entity_version=ENTITY_VERSION,
                        entity=completed_job,
                        meta={}
                    )
                    # Update brands cache record in the external service.
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                        entity={"data": brands_data},
                        meta={}
                    )
                else:
                    error_job = {
                        "job_id": job_id,
                        "requestedAt": requested_at,
                        "status": "error",
                        "brands": []
                    }
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="jobs",
                        entity_version=ENTITY_VERSION,
                        entity=error_job,
                        meta={}
                    )
    except Exception as e:
        error_job = {
            "job_id": job_id,
            "requestedAt": requested_at,
            "status": "error",
            "brands": []
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="jobs",
            entity_version=ENTITY_VERSION,
            entity=error_job,
            meta={}
        )

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