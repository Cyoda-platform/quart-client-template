import asyncio
import uuid
import time
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache to store job data
jobs = {}

# TODO: In a real implementation, consider a persistent storage or a proper caching strategy.
# For the prototype, we are using a simple dictionary.

@app.route('/fetch_data', methods=['POST'])
async def fetch_data():
    data = await request.get_json()
    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    # Extract request parameters with defaults
    company_name = data.get("company_name", "ryanair")
    skip = data.get("skip", 0)
    max_results = data.get("max", 5)

    # Generate a unique job_id for tracking the request
    job_id = str(uuid.uuid4())
    requested_at = time.time()
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "data": None}

    # Fire and forget task to process the external API call and processing
    asyncio.create_task(process_entity(job_id, {"company_name": company_name, "skip": skip, "max": max_results}))

    return jsonify({
        "message": "Data retrieval initiated",
        "job_id": job_id
    }), 201

async def process_entity(job_id, params):
    # Construct the external API URL based on provided parameters
    company_name = params.get("company_name", "ryanair")
    skip = params.get("skip", 0)
    max_results = params.get("max", 5)
    url = f"https://services.cro.ie/cws/companies?&company_name={company_name}&skip={skip}&max={max_results}&htmlEnc=1"
    
    # Prepare headers. Basic authentication is included in the header.
    headers = {
        "Authorization": "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"
    }
    
    # TODO: Evaluate if additional authentication details are needed (e.g., using aiohttp.BasicAuth).
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    external_data = await resp.json()
                else:
                    external_data = {
                        "error": "Failed to fetch data",
                        "status": resp.status
                    }
    except Exception as e:
        external_data = {
            "error": "Exception during external API call",
            "details": str(e)
        }
    
    # Simulate additional processing or calculations here if necessary.
    # TODO: Perform any required business logic or data transformations.
    
    # Update local cache with the fetched data
    jobs[job_id]["data"] = external_data
    jobs[job_id]["status"] = "completed"

@app.route('/company_data', methods=['GET'])
async def get_company_data():
    # For the prototype, return all jobs in the cache.
    # TODO: In a future iteration, consider filtering or retrieving data by job_id.
    return jsonify({
        "data": jobs
    }), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)