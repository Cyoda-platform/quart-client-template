import asyncio
import datetime
import uuid

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# Global in-memory "persistence" mocks for job status and brands data
jobs = {}      # { job_id: { "status": "processing", "requestedAt": <timestamp>, "brands": [...] } }
brands_cache = []  # Stores the latest fetched brands data

@app.route('/brands/fetch', methods=['POST'])
async def fetch_brands():
    """
    POST endpoint to trigger the fetching of brand data from the external API.
    Any business logic and calculations take place in this POST endpoint.
    """
    request_data = await request.get_json() or {}
    force_refresh = request_data.get("force_refresh", False)  # Not used in this prototype; placeholder for caching logic

    # Generate a job_id and record the job start time
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at, "brands": []}

    # Fire and forget the processing task.
    # Using create_task to process the external API request in the background.
    asyncio.create_task(process_brands_fetch(job_id))

    return jsonify({
        "status": "success",
        "message": "Brands fetch job started.",
        "job_id": job_id
    })


async def process_brands_fetch(job_id):
    """
    Asynchronous task that calls the external API,
    processes the data, and updates the in-memory cache.
    """
    url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    brands_data = await resp.json()
                    
                    # TODO: Implement any specific business logic or data transformation here
                    # For now, we simply store the raw data.
                    
                    # Update the global cache
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
    """
    GET endpoint to retrieve the stored list of brands.
    This endpoint only returns the data that has already been processed.
    """
    # If no data has been fetched yet, the brands_cache might be empty.
    return jsonify({
        "status": "success",
        "data": brands_cache
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)