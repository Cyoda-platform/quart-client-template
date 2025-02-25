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
# processes it, and updates the entity state. Errors are caught and marked in the entity.
async def process_brands(entity):
    external_url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_url, headers={"accept": "application/json"}) as resp:
                if resp.status != 200:
                    # Mark the entity as failed if external request does not succeed.
                    entity["status"] = "failed"
                    entity["error"] = f"Failed to fetch external data, HTTP status: {resp.status}"
                    entity["processedAt"] = datetime.utcnow().isoformat()
                    return entity
                raw_data = await resp.json()
    except Exception as e:
        # Catch any exception during external API call.
        entity["status"] = "failed"
        entity["error"] = f"Exception during external API call: {str(e)}"
        entity["processedAt"] = datetime.utcnow().isoformat()
        return entity

    try:
        # Process and update the entity with fetched data.
        entity["raw_data"] = raw_data
        # Example transformation: promote raw_data to data field.
        entity["data"] = raw_data
        entity["status"] = "completed"
        entity["processedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        # Catch exceptions during processing.
        entity["status"] = "failed"
        entity["error"] = f"Exception during processing: {str(e)}"
        entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

@app.route('/brands', methods=['POST'])
@validate_request(BrandFilter)
async def create_brands(data: BrandFilter):
    # Build filter parameters if provided.
    filters = {"filter": data.filter, "limit": data.limit} if data else {}
    # Create initial entity data with minimal details.
    initial_data = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "filters": filters
    }
    # The workflow function process_brands is applied to the entity asynchronously before persistence.
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
            entity=initial_data,
            workflow=process_brands
        )
    except Exception as e:
        # In case add_item fails, return a proper error.
        return jsonify({"error": f"Failed to create brand job: {str(e)}"}), 500

    return jsonify({
        "job_id": job_id
    }), 201

@validate_querystring(BrandQuery)
@app.route('/brands', methods=['GET'])
async def get_brands():
    job_id = request.args.get("job_id")
    if job_id:
        try:
            job = await entity_service.get_item(
                token=cyoda_token,
                entity_model="brands",
                entity_version=ENTITY_VERSION,
                technical_id=job_id
            )
        except Exception as e:
            return jsonify({"error": f"Failed to retrieve job: {str(e)}"}), 500

        if job is None:
            return jsonify({"error": "Job not found"}), 404
        if job.get("status") != "completed":
            return jsonify({
                "status": job.get("status"),
                "message": "Data processing in progress"
            }), 202
        return jsonify(job.get("data")), 200
    else:
        try:
            items = await entity_service.get_items(
                token=cyoda_token,
                entity_model="brands",
                entity_version=ENTITY_VERSION
            )
        except Exception as e:
            return jsonify({"error": f"Failed to retrieve jobs: {str(e)}"}), 500

        # Filter for completed jobs.
        completed_jobs = [item for item in items if item.get("status") == "completed"]
        if not completed_jobs:
            return jsonify({"message": "No completed job data available"}), 404
        # For simplicity, return the data of the first completed job.
        return jsonify(completed_jobs[0].get("data")), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)