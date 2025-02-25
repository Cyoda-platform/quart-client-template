import asyncio
import uuid
import datetime
import aiohttp

from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Global in-memory cache for brand data and jobs.
BRAND_DATA = []  # This acts as our persistence placeholder.
JOBS = {}        # Dictionary to hold job statuses.

EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/brands"


async def process_entity(job, options):
    """
    Process the job: fetch data from the external API, update global BRAND_DATA,
    and update the job status.
    """
    # Retrieve optional parameters with defaults.
    fetch_timeout_ms = options.get("fetchTimeout", 5000)
    # Convert milliseconds to seconds for aiohttp timeout.
    timeout_secs = fetch_timeout_ms / 1000

    # TODO: Handle the 'forceUpdate' flag if needed (for cache bypass logic).
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_secs)) as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as response:
                if response.status == 200:
                    data = await response.json()
                    # Process the JSON data here if any additional transformation is needed.
                    global BRAND_DATA
                    BRAND_DATA = data  # Update the in-memory cache.
                    # Update job status.
                    job["status"] = "completed"
                    job["completedAt"] = datetime.datetime.utcnow().isoformat()
                    return data
                else:
                    job["status"] = "error"
                    job["error"] = f"Received unexpected status: {response.status}"
                    # TODO: Implement more robust error handling/logging as necessary.
                    return None
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        # TODO: Add exception logging.
        return None


@app.route('/api/brands/update', methods=['POST'])
async def update_brands():
    """
    Initiates fetching data from the external API, processing it, and updating the local cache.
    """
    # Read optional parameters from the request JSON payload.
    data = await request.get_json(silent=True) or {}
    # Create a job id and initialize its status.
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    JOBS[job_id] = job

    # Fire and forget processing task.
    # Here we await on the task to return the latest brand data.
    # TODO: Consider running process_entity as a background task without awaiting if UX demands asynchronous updates.
    result = await asyncio.create_task(process_entity(job, data))
    
    if result is not None:
        return jsonify({
            "status": "success",
            "data": result,
            "message": "Brand data successfully updated from external source.",
            "jobId": job_id
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to fetch/update brand data.",
            "jobId": job_id,
            "details": job.get("error", "Unknown error")
        }), 500


@app.route('/api/brands', methods=['GET'])
async def get_brands():
    """
    Retrieves the current stored brand data from the in-memory cache.
    """
    if BRAND_DATA:
        return jsonify({
            "status": "success",
            "data": BRAND_DATA
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "No brand data available. Please update the data by sending a POST request."
        }), 404


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)