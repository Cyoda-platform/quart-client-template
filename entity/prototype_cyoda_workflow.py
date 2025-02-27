#!/usr/bin/env python3
import asyncio
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, request
import aiohttp
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Local in‑memory job tracker.
entity_job = {}

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class FetchBrandsRequest:
    # Using a dummy field as a workaround for empty body validation.
    dummy: str = ""

# Workflow function applied to the entity before persistence.
async def process_brands(entity_data):
    # Modify the entity data as needed before it is persisted.
    entity_data['workflow_processed'] = True
    entity_data['processed_at'] = datetime.utcnow().isoformat()
    return entity_data

async def process_entity(entity_job, job_id, data):
    # Use external service to add the item with a workflow processing step.
    item_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data,  # the validated data object
        workflow=process_brands  # Workflow function applied to the entity asynchronously before persistence.
    )
    # Update job status to success and store the item id for retrieval via separate endpoint.
    entity_job[job_id]["status"] = "success"
    entity_job[job_id]["id"] = item_id

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    # Generate a job_id based on current timestamp.
    job_id = str(datetime.utcnow().timestamp())
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Using aiohttp.ClientSession for the external API call.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    api_data = await resp.json()
                    # Fire and forget the processing task.
                    await asyncio.create_task(process_entity(entity_job, job_id, api_data))
                else:
                    entity_job[job_id]["status"] = "error"
                    return jsonify({
                        "status": "error",
                        "message": f"Failed to fetch brand data: HTTP {resp.status}"
                    }), resp.status
        except Exception as e:
            entity_job[job_id]["status"] = "error"
            return jsonify({
                "status": "error",
                "message": f"Exception during data retrieval: {str(e)}"
            }), 500

    return jsonify({
        "status": "success",
        "message": "External data retrieved and processed successfully.",
        "jobId": job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve brands using the external entity_service.
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if items:
        return jsonify(items)
    else:
        return jsonify({
            "status": "error",
            "message": "No brand data available. Please trigger data fetching."
        }), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)