import asyncio
import datetime
import uuid
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Workaround: For POST endpoints, place validate_request after route decorator

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchBrandsRequest:
    force_refresh: bool = False

# Global in-memory "persistence" mocks for job status and brands data
jobs = {}      # { job_id: { "status": "processing", "requestedAt": <timestamp>, "brands": [...] } }
brands_cache = []  # Stores the latest fetched brands data

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)  # Workaround: validate_request must be placed after the route decorator for POST endpoints
async def fetch_brands(data: FetchBrandsRequest):
    force_refresh = data.force_refresh  # Although not used in this prototype, available for potential caching logic

    # Generate a job_id and record the job start time
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "brands": []}

    # Fire and forget the processing task.
    asyncio.create_task(process_brands_fetch(job_id))

    return jsonify({
        "status": "success",
        "message": "Brands fetch job started.",
        "job_id": job_id
    })

async def process_brands_fetch(job_id):
    url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    brands_data = await resp.json()
                    # TODO: Implement any specific business logic or data transformation here
                    global brands_cache
                    brands_cache = brands_data
                    jobs[job_id]["status"] = "completed"
                    jobs[job_id]["brands"] = brands_data
                else:
                    jobs[job_id]["status"] = "error"
                    # TODO: Log the status code error or add further error handling if required.
    except Exception as e:
        jobs[job_id]["status"] = "error"
        # TODO: Log exception details for deeper insight during non-prototype implementation.

@app.route('/brands', methods=['GET'])
async def get_brands():
    # GET endpoint does not require validation as it does not accept a request body or query parameters.
    return jsonify({
        "status": "success",
        "data": brands_cache
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)