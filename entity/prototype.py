import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # Using validate_request for POST endpoints

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Dataclass for POST endpoint request validation
@dataclass
class SyncRequest:
    query: str = ""  # Placeholder for filter options; TODO: update with proper structure if needed

# Global in-memory persistence mocks
brands_cache = []  # Stores the brands data from the last sync
jobs = {}  # Stores job information for background processing

EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/brands"

async def process_entity(job_id: str, data: list) -> None:
    """
    Process entity data and update the cache and job status.
    This function simulates processing delay.
    """
    # TODO: Add any additional data transformations or calculations as needed.
    await asyncio.sleep(1)  # Simulated delay for processing
    global brands_cache
    brands_cache = data
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()

# For POST endpoints, the route decorator must come first then the validate_request decorator.
@app.route("/api/brands/sync", methods=["POST"])
@validate_request(SyncRequest)  # This is placed second due to a known issue/workaround with quart-schema
async def sync_brands(data: SyncRequest):
    """
    Endpoint to sync brand details from the external API.
    Business logic includes:
      - Calling the external API using aiohttp.ClientSession
      - Processing the returned data asynchronously
      - Updating an in-memory cache (brands_cache)
    """
    requested_at = datetime.utcnow().isoformat()
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # TODO: Utilize data.query from the validated request if filtering needs to be implemented.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as resp:
                if resp.status != 200:
                    jobs[job_id]["status"] = "failed"
                    return jsonify({
                        "status": "error",
                        "message": f"External API returned status code {resp.status}"
                    }), resp.status
                external_data = await resp.json()
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        return jsonify({
            "status": "error",
            "message": f"Error fetching data from external API: {str(e)}"
        }), 500

    # Fire and forget the processing task.
    # TODO: Adjust processing logic as needed.
    asyncio.create_task(process_entity(job_id, external_data))

    # For the prototype, we wait slightly longer than the simulated processing delay.
    await asyncio.sleep(1.1)  # Waiting a bit longer than process_entity's simulated delay

    # Return the processed data. Assumes that process_entity has updated the cache.
    return jsonify({
        "status": "success",
        "jobId": job_id,
        "data": brands_cache
    }), 200

# GET endpoint with no validation as no query parameters are expected.
@app.route("/api/brands", methods=["GET"])
async def get_brands():
    """
    Endpoint to retrieve the stored brand details.
    """
    if not brands_cache:
        # TODO: Decide on the appropriate response when no data is available.
        return jsonify({
            "status": "error",
            "message": "No brand data available. Please trigger /api/brands/sync first."
        }), 404
    return jsonify({
        "status": "success",
        "data": brands_cache
    }), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)