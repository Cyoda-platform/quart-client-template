import asyncio
import uuid
import datetime
from quart import Quart, request, jsonify
import aiohttp
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema for the app

# Global in-memory storage as a mock for persistence
BRAND_CACHE = []  # TODO: Replace with a proper datastore in production
JOBS = {}         # Store job status and metadata

async def process_entity(job, payload):
    # TODO: Use payload for additional processing if needed.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as response:
                data = await response.json()
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            # TODO: Add proper error handling/logging as needed.
            return
    
    # Process and transform the data if required.
    # Here we simply store the data as is.
    global BRAND_CACHE
    BRAND_CACHE = data
    job["status"] = "completed"
    job["completedAt"] = datetime.datetime.utcnow().isoformat()
    # TODO: Perform any additional calculations or data transformations if required.

@app.route('/api/brands/fetch', methods=['POST'])
async def fetch_brands():
    # Get the incoming JSON request; dynamic schema so no strict validation.
    request_data = await request.get_json()
    
    # Create a job record to track the processing status.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}
    
    # Fire and forget the processing task.
    await asyncio.create_task(process_entity(JOBS[job_id], request_data))
    
    # Return response indicating that the data fetch was successful.
    response = {
        "status": "success",
        "message": "Data fetched and stored successfully.",
        "data": BRAND_CACHE,
        "job_id": job_id  # Included for tracking purposes.
    }
    return jsonify(response), 200

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # Return the stored brand data from our in-memory cache.
    return jsonify(BRAND_CACHE), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)