import asyncio
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, jsonify, request
import aiohttp
from quart_schema import QuartSchema, validate_request

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for persistence between calls.
brand_data_cache = {}

# Local in-memory job tracker.
entity_job = {}

@dataclass
class FetchBrandsRequest:
    # TODO: Define any request parameters if necessary; currently using dummy field.
    dummy: str = ""  # Using a dummy field as a workaround for empty body validation.

async def process_entity(entity_job, job_id, data):
    # TODO: Implement any additional processing or transformation if necessary.
    await asyncio.sleep(0)  # Simulate processing delay if needed.
    # Store the data in the local cache.
    brand_data_cache['brands'] = data
    # Update job status to success.
    entity_job[job_id]["status"] = "success"

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)  # NOTE: For POST requests, validate_request is placed after the route decorator (workaround for quart-schema issue).
async def fetch_brands(data: FetchBrandsRequest):
    # Generate a job_id based on current timestamp.
    job_id = str(datetime.utcnow().timestamp())
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Using aiohttp.ClientSession for the external API call.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    api_data = await resp.json()
                    # Fire and forget the processing task.
                    await asyncio.create_task(process_entity(entity_job, job_id, api_data))
                else:
                    entity_job[job_id]["status"] = "error"
                    return jsonify({
                        "status": "error",
                        "message": f"Failed to fetch brand data: HTTP {resp.status}"
                    }), resp.status
        except Exception as e:
            entity_job[job_id]["status"] = "error"
            return jsonify({
                "status": "error",
                "message": f"Exception during data retrieval: {str(e)}"
            }), 500

    return jsonify({
        "status": "success",
        "message": "External data retrieved and processed successfully.",
        "jobId": job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    # No request validation is added here since GET requests without parameters do not require it.
    if 'brands' in brand_data_cache:
        return jsonify(brand_data_cache['brands'])
    else:
        return jsonify({
            "status": "error",
            "message": "No brand data available. Please trigger data fetching."
        }), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)