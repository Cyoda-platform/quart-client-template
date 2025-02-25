import asyncio
import uuid
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
    filter: str = ""  # Optional filter, defaults to empty string
    limit: int = 0    # Optional limit on results, defaults to 0 (no limit)

@dataclass
class BrandQuery:
    job_id: str = ""  # Optional job_id for GET request queries

# Removed local in-memory cache. Use the external entity_service instead.

async def process_entity(job_id, raw_data, filters):
    # Simulate any business logic processing
    await asyncio.sleep(1)  # Simulate processing time
    processed = raw_data  # In a full implementation, apply filtering or transformation as needed.
    updated_data = {
        "status": "completed",
        "data": processed,
        "processedAt": datetime.utcnow().isoformat()
    }
    # Update the external entity with processed data.
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=updated_data,
        meta={"technical_id": job_id}
    )
    return

@app.route('/brands', methods=['POST'])
@validate_request(BrandFilter)
async def create_brands(data: BrandFilter):
    filters = {"filter": data.filter, "limit": data.limit} if data else {}
    
    external_url = "https://api.practicesoftwaretesting.com/brands"
    async with aiohttp.ClientSession() as session:
        async with session.get(external_url, headers={"accept": "application/json"}) as resp:
            if resp.status != 200:
                # Enhance error handling for external API failures.
                return jsonify({"error": "Failed to fetch external data"}), resp.status
            raw_data = await resp.json()
    
    # Create a new entity item via the external service.
    initial_data = {
        "status": "processing",
        "raw_data": raw_data,
        "requestedAt": datetime.utcnow().isoformat(),
        "filters": filters
    }
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
        entity=initial_data
    )
    
    # Fire and forget the background processing task.
    asyncio.create_task(process_entity(job_id, raw_data, filters))
    
    # Return only the job_id; the processed result will be fetched separately.
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