#!/usr/bin/env python3
"""
prototype.py
A working prototype for fetching and serving brand data using Quart and aiohttp.
This prototype demonstrates the basic UX and identifies potential gaps before a full implementation.
"""

import asyncio
import uuid
from datetime import datetime

from quart import Quart, jsonify, request
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Global in-memory storage for caching fetched brands and job statuses.
cached_brands = None  # Will hold the processed brand data.
jobs = {}  # Example: jobs[job_id] = {"status": "processing", "requestedAt": timestamp}


async def process_entity(job_id):
    """
    Asynchronous background task to fetch brand data from the external API,
    process it, and update the cache.
    """
    global cached_brands, jobs

    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    headers = {"accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # TODO: Perform any additional processing/transformation of the data if required.
                    cached_brands = data
                    jobs[job_id]["status"] = "completed"
                else:
                    jobs[job_id]["status"] = "failed"
                    # TODO: Add more detailed error handling/logging.
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            # TODO: Log the error properly.
            print(f"Error processing job {job_id}: {e}")


@app.route("/api/brands/fetch", methods=["POST"])
async def fetch_brands():
    """
    POST endpoint to trigger fetching of brand data from the external API.
    This endpoint starts an asynchronous background task to process the data.
    """
    global jobs

    # Generate a unique job ID and record the job start time and status.
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Fire-and-forget the processing task.
    asyncio.create_task(process_entity(job_id))

    # Return immediate response; processed data will be available via the GET endpoint.
    return jsonify({
        "status": "success",
        "job_id": job_id,
        "message": "Data fetch initiated."
    })


@app.route("/api/brands", methods=["GET"])
async def get_brands():
    """
    GET endpoint to return the cached brand data.
    If no data is available, informs the user accordingly.
    """
    global cached_brands
    if cached_brands is not None:
        return jsonify({
            "status": "success",
            "data": cached_brands
        })
    else:
        # TODO: Consider handling the scenario where live processing is still ongoing.
        return jsonify({
            "status": "pending",
            "message": "Brand data is not yet available. Please try again shortly."
        })


if __name__ == "__main__":
    app.run(
        use_reloader=False,
        debug=True,
        host="0.0.0.0",
        port=8000,
        threaded=True
    )