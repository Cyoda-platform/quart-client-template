import asyncio
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

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


@app.route("/api/brands/sync", methods=["POST"])
async def sync_brands():
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

    # Optional: Process any filters from request body in the future.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as resp:
                if resp.status != 200:
                    jobs[job_id]["status"] = "failed"
                    return jsonify({
                        "status": "error",
                        "message": f"External API returned status code {resp.status}"
                    }), resp.status
                data = await resp.json()
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        return jsonify({
            "status": "error",
            "message": f"Error fetching data from external API: {str(e)}"
        }), 500

    # Fire and forget the processing task.
    # TODO: If further processing logic is added, adjust this task accordingly.
    asyncio.create_task(process_entity(job_id, data))

    # For the prototype, we wait shortly to simulate processing completion.
    # In a production scenario, you might want to return a job id and let the user poll for the result.
    await asyncio.sleep(1.1)  # Waiting a bit longer than process_entity simulated delay

    # Return the processed data. Assumes that process_entity has updated the cache.
    return jsonify({
        "status": "success",
        "jobId": job_id,
        "data": brands_cache
    }), 200


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