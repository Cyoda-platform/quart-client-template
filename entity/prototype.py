```python
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache to mock persistence (job_id -> job info)
entity_jobs = {}

# Example external API to demonstrate real HTTP call:
# Using a public free API that returns a random joke (https://icanhazdadjoke.com/api)
EXTERNAL_API_URL = "https://icanhazdadjoke.com/"

async def fetch_external_data():
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(EXTERNAL_API_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
            # Extract joke text as example external data
            return data.get("joke", "No joke found")
        except Exception as e:
            logger.exception("Failed to fetch external data")
            raise e

async def process_entity(job_store, job_id, input_data):
    try:
        logger.info(f"Processing job {job_id} with input: {input_data}")

        # Simulate external API call as part of business logic
        external_info = await fetch_external_data()

        # TODO: Add any specific calculations or business logic here
        # For demo, just combine input and external data in the result
        result_data = {
            "inputReceived": input_data,
            "externalInfo": external_info,
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }

        # Update job status and result atomically
        job_store[job_id].update({
            "status": "completed",
            "resultData": result_data,
            "completedAt": datetime.utcnow()
        })

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        job_store[job_id].update({
            "status": "failed",
            "error": str(e),
            "completedAt": datetime.utcnow()
        })
        logger.exception(f"Job {job_id} failed during processing")

@app.route('/process', methods=['POST'])
async def process():
    data = await request.get_json()

    if data is None:
        return jsonify({"error": "Missing JSON body"}), 400

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow()

    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "resultData": None,
        "error": None
    }

    # Fire and forget processing task
    asyncio.create_task(process_entity(entity_jobs, job_id, data))

    return jsonify({
        "processId": job_id,
        "status": "processing"
    }), 202

@app.route('/result/<process_id>', methods=['GET'])
async def get_result(process_id):
    job = entity_jobs.get(process_id)
    if job is None:
        return jsonify({"error": "processId not found"}), 404

    response = {
        "processId": process_id,
        "status": job["status"],
        "resultData": job.get("resultData")
    }
    if job["status"] == "failed":
        response["error"] = job.get("error")

    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
