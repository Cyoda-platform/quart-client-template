import asyncio
import uuid
import datetime
import logging
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For GET requests with querystring, use validate_querystring if needed.
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize the schema (data validations are dynamic)

# Dummy dataclass for POST request validation in /brands/fetch.
@dataclass
class FetchBrandsRequest:
    # Dummy field; TODO: Add actual fields if parameters are needed.
    dummy: str = ""

# In-memory cache and jobs store (mock persistence)
cached_brands = None  # Will hold the processed brand data
last_updated = None  # Timestamp of the last successful fetch
jobs = {}  # Dictionary to store job statuses; key: job_id, value: details dict

EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/brands"

async def process_brands(job_id: str):
    global cached_brands, last_updated

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as response:
                if response.status != 200:
                    # TODO: Handle non-200 external responses if necessary.
                    jobs[job_id]["status"] = "failed"
                    logging.error(f"External API returned status {response.status}")
                    return

                external_data = await response.json()

                # TODO: Add any additional calculations or data transformations here.
                # For now, we directly assign the external API response.
                processed_data = external_data

                # Mock persistence: update the local cache.
                cached_brands = processed_data
                last_updated = datetime.datetime.utcnow().isoformat() + "Z"

                # Update job status.
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

                return processed_data

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        logging.exception("Error processing brands")
        # TODO: Further error handling/logging can be added if necessary.

# For POST endpoints, due to an issue in Quart Schema, the @validate_request decorator is placed after the route decorator.
@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)  # Workaround: For POST, validator decorator goes after route decorator.
async def fetch_brands(data: FetchBrandsRequest):
    # Setup job tracking.
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task.
    # In this prototype, we await the task so the response includes processed data.
    processed_data = await asyncio.create_task(process_brands(job_id))

    if processed_data is None:
        response = {
            "success": False,
            "job_id": job_id,
            "message": "Failed to fetch external source data."
        }
        status_code = 500
    else:
        response = {
            "success": True,
            "job_id": job_id,
            "data": processed_data,
            "message": "External source data fetched and processed successfully"
        }
        status_code = 200

    return jsonify(response), status_code

# GET /brands does not require validation as no request parameters are expected.
@app.route('/brands', methods=['GET'])
async def get_brands():
    if cached_brands is None:
        response = {
            "data": [],
            "last_updated": None,
            "message": "No data available. Please trigger data fetching via POST /brands/fetch"
        }
        status_code = 404
    else:
        response = {
            "data": cached_brands,
            "last_updated": last_updated
        }
        status_code = 200

    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)