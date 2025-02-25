import asyncio
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for storing processed brand data.
BRANDS_CACHE = {}

# In-memory store to simulate job tracking.
entity_jobs = {}

async def process_entity(job_id, data):
    # TODO: Replace with actual processing logic if required.
    await asyncio.sleep(1)  # Simulate processing delay.
    
    # For prototype purposes, we directly update the cache with external data.
    BRANDS_CACHE['brands'] = data  # Overwrites previous data.
    
    # Update the job status.
    entity_jobs[job_id]['status'] = 'completed'

@app.route('/fetch-brands', methods=['POST'])
async def fetch_brands():
    # TODO: Generate a unique job_id and capture the current timestamp.
    job_id = "job_placeholder"
    requested_at = "timestamp_placeholder"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fetch data from the external API.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status != 200:
                    return jsonify({"error": "Failed to fetch external data."}), 500
                data = await resp.json()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))
    
    return jsonify({
        "message": "Data fetched successfully.",
        "data": data
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve the processed brand data from the in-memory cache.
    data = BRANDS_CACHE.get('brands', [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)