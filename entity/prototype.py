import asyncio
import aiohttp
import uuid
from datetime import datetime
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Import validate_request

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Data class for validating POST request body for /api/brands/fetch
@dataclass
class FetchRequest:
    force_refresh: bool = False

# Global in-memory cache for brand data
brands_cache = []

# Global in-memory store for jobs (mock persistence)
entity_job = {}

async def process_entity(job, data):
    # Simulate some processing delay
    # TODO: Replace with real processing logic if needed.
    await asyncio.sleep(1)
    # For this prototype, we simply update the global cache with the data.
    global brands_cache
    brands_cache = data
    job["status"] = "completed"
    job["completedAt"] = datetime.utcnow().isoformat()

# For POST endpoints, the route decorator comes first followed by the validate_request decorator.
# This is a workaround for an issue in the Quart Schema library.

@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)  # Validate request body after route decorator for POST endpoints
async def fetch_brands(data: FetchRequest):
    force_refresh = data.force_refresh

    # Generate a unique job id and register the job
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.practicesoftwaretesting.com/brands", headers={"accept": "application/json"}) as resp:
                if resp.status != 200:
                    # TODO: Add better error handling and logging as needed.
                    return jsonify({"status": "error", "message": "Failed to fetch brand data from external API"}), resp.status
                external_data = await resp.json()
    except Exception as e:
        # TODO: Enhance exception handling based on actual failure modes.
        return jsonify({"status": "error", "message": "Exception occurred while fetching data", "detail": str(e)}), 500

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_job[job_id], external_data))

    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated. Processing in background.",
        "job_id": job_id,
        "data_count": len(external_data)  # number of brands processed (will be updated when job is complete)
    })


@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # No validation is added for GET requests without parameters.
    global brands_cache
    return jsonify(brands_cache)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)