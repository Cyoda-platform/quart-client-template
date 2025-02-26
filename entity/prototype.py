import asyncio
import uuid
import time
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For GET, no validate_querystring needed as there are no query parameters

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache to store job data
jobs = {}

# TODO: In a real implementation, consider a persistent storage or a proper caching strategy.
# For the prototype, we are using a simple dictionary.

@dataclass
class FetchDataRequest:
    company_name: str
    skip: int
    max: int

# For POST requests, per quart-schema workaround, validation decorator is applied after the route decorator.
@app.route('/fetch_data', methods=['POST'])
@validate_request(FetchDataRequest)  # Workaround: For POST endpoints, validation comes after route declaration.
async def fetch_data(data: FetchDataRequest):
    # Extract request parameters (defaults can be handled at client side if missing)
    company_name = data.company_name if data.company_name else "ryanair"
    skip = data.skip
    max_results = data.max

    # Generate a unique job_id for tracking the request
    job_id = str(uuid.uuid4())
    requested_at = time.time()
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "data": None}

    # Fire and forget task to process the external API call and processing
    asyncio.create_task(process_entity(job_id, {
        "company_name": company_name,
        "skip": skip,
        "max": max_results
    }))

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
        "Authorization": "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw",
        "Content-Type": "application/json"
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
    
    # TODO: Perform any required business logic or data transformations.
    
    # Update local cache with the fetched data
    jobs[job_id]["data"] = external_data
    jobs[job_id]["status"] = "completed"

# GET endpoint without request parameters, so no validation decorator is used.
@app.route('/company_data', methods=['GET'])
async def get_company_data():
    # For the prototype, return all jobs in the cache.
    # TODO: In a future iteration, consider filtering or retrieving data by job_id.
    return jsonify({
        "data": jobs
    }), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)