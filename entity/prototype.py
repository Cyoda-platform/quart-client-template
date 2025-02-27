from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request as per quart-schema workaround
import aiohttp
import asyncio
from uuid import uuid4
from datetime import datetime

app = Quart(__name__)
QuartSchema(app)

# Data class for POST request validation
@dataclass
class BrandRequest:
    filter: str = None  # Optional filter parameter; TODO: adjust fields as requirements are clarified.

# Global local cache for processed brands
PROCESSED_DATA = []
# Global job tracker (mock persistence)
ENTITY_JOBS = {}

async def process_entity(job_id, params: dict):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # TODO: Apply additional business logic or calculations if required.
                    global PROCESSED_DATA
                    PROCESSED_DATA = data  # Store the processed data in the local cache.
                    ENTITY_JOBS[job_id]["status"] = "completed"
                else:
                    ENTITY_JOBS[job_id]["status"] = "failed"
                    # TODO: Log error details and handle error response properly.
        except Exception as e:
            ENTITY_JOBS[job_id]["status"] = "failed"
            # TODO: Handle exception properly (e.g., logging the error details).
            print(f"Error processing job {job_id}: {e}")

@app.route('/api/brands', methods=['POST'])
@validate_request(BrandRequest)  # Workaround: for POST, validation decorator goes after the route decorator.
async def fetch_and_process_brands(data: BrandRequest):
    # Access validated request data from the dataclass
    req_params = data.__dict__
    job_id = str(uuid4())
    ENTITY_JOBS[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }
    # Fire and forget the processing task.
    task = asyncio.create_task(process_entity(job_id, req_params))
    await task  # In this prototype, we wait for the task to complete.
    response = {
        "status": "success",
        "data": PROCESSED_DATA,
        "jobId": job_id  # Optional: expose job id for tracking purposes.
    }
    return jsonify(response)

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    response = {
        "data": PROCESSED_DATA
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)