#!/usr/bin/env python3
import asyncio
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class BrandFilter:
    filter: str = ""  # Optional filter; defaults to empty string
    limit: int = 0    # Optional limit on results; defaults to 0 (no limit)

@dataclass
class BrandQuery:
    job_id: str = ""  # Optional job_id for GET request queries

# Workflow function applied to the entity asynchronously before persistence.
# It takes the entity data as the only argument. This function fetches external data,
# updates the entity state and returns the updated entity.
async def process_brands(entity):
    external_url = "https://api.practicesoftwaretesting.com/brands"
    async with aiohttp.ClientSession() as session:
        async with session.get(external_url, headers={"accept": "application/json"}) as resp:
            if resp.status != 200:
                # Mark entity as failed if external request fails.
                entity["status"] = "failed"
                entity["error"] = f"Failed to fetch external data, status {resp.status}"
                return entity
            raw_data = await resp.json()
    # Process and update the entity.
    entity["raw_data"] = raw_data
    entity["data"] = raw_data  # Example transformation: promote raw_data to data field.
    entity["status"] = "completed"
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

@app.route('/brands', methods=['POST'])
@validate_request(BrandFilter)
async def create_brands(data: BrandFilter):
    filters = {"filter": data.filter, "limit": data.limit} if data else {}
    
    # Initial entity has minimal data; the workflow function will handle external data fetching.
    initial_data = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "filters": filters
    }
    # The workflow function process_brands is applied to the entity asynchronously before persistence.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=initial_data,
        workflow=process_brands
    )
    return jsonify({
        "job_id": job_id
    }), 201

@validate_querystring(BrandQuery)
@app.route('/brands', methods=['GET'])
async def get_brands():
    job_id = request.args.get("job_id")
    
    if job_id:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        if job.get("status") != "completed":
            return jsonify({
                "status": job.get("status"),
                "message": "Data processing in progress"
            }), 202
        return jsonify(job.get("data")), 200
    else:
        # Retrieve all items and filter for completed jobs.
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
        completed_jobs = [item for item in items if item.get("status") == "completed"]
        if not completed_jobs:
            return jsonify({"message": "No completed job data available"}), 404
        # For simplicity, return the data of the first completed job.
        return jsonify(completed_jobs[0].get("data")), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)