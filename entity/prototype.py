import asyncio
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence
entity_jobs = {}

async def process_entity(job_id, raw_data, filters):
    # TODO: Implement any necessary business logic operations
    # For this prototype, we simulate processing delay and pass through the data.
    await asyncio.sleep(1)  # Simulate processing time
    # TODO: Apply filter logic based on `filters` if provided.
    processed = raw_data  # In a full implementation, modify the data as needed.
    entity_jobs[job_id]['status'] = 'completed'
    entity_jobs[job_id]['data'] = processed
    return

@app.route('/brands', methods=['POST'])
async def create_brands():
    req_data = await request.get_json()
    filters = req_data if req_data else {}
    
    # Generate a unique job identifier and initialize job record.
    job_id = str(uuid.uuid4())
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }
    
    external_url = "https://api.practicesoftwaretesting.com/brands"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(external_url, headers={"accept": "application/json"}) as resp:
            if resp.status != 200:
                # TODO: Enhance error handling for external API failures.
                return jsonify({"error": "Failed to fetch external data"}), resp.status
            raw_data = await resp.json()
    
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, raw_data, filters))
    
    return jsonify({
        "job_id": job_id,
        "data": raw_data  # Return raw data immediately for UX preview; processed data may differ.
    }), 201

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve a specific job result if `job_id` is provided.
    job_id = request.args.get("job_id")
    
    if job_id:
        job = entity_jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found"}), 404
        if job["status"] != "completed":
            return jsonify({
                "status": job["status"],
                "message": "Data processing in progress"
            }), 202
        return jsonify(job["data"]), 200
    else:
        # If no job_id is provided, return aggregated result from completed jobs.
        completed_jobs = [job["data"] for job in entity_jobs.values() if job.get("status") == "completed"]
        if not completed_jobs:
            return jsonify({"message": "No completed job data available"}), 404
        # TODO: In production implement proper pagination and choose appropriate data.
        return jsonify(completed_jobs[0]), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)