import asyncio
import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema  # Schema integration, dynamic data so no validate_request

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for processed brands data (persistence mock)
cached_brands = None

async def fetch_brands():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'https://api.practicesoftwaretesting.com/brands',
            headers={'accept': 'application/json'}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                # TODO: handle non-200 responses appropriately
                return None

async def process_entity(data):
    # Placeholder for additional processing logic if necessary.
    # For prototype, we assume data is already well-formed.
    await asyncio.sleep(0.1)  # Simulate processing delay
    return data

async def process_entity_task(entity_job, data):
    global cached_brands
    # Process the raw data
    processed_data = await process_entity(data)
    # Update in-memory cache as a persistence mock
    cached_brands = processed_data
    # Update job status (in a real implementation, persist the job state properly)
    entity_job['status'] = "completed"
    # TODO: Add proper logging and job persistence if needed.

@app.route('/brands', methods=['POST'])
async def post_brands():
    global cached_brands
    # Read optional payload (for future extensions like filtering options)
    payload = await request.get_json(silent=True)
    # TODO: Process payload if filtering or other parameters are required

    # Trigger external API call to fetch brands data
    brands_data = await fetch_brands()
    if brands_data is None:
        return jsonify({"error": "Failed to fetch brands data"}), 500

    # Create a job entry placeholder for processing
    job_id = "job_" + str(asyncio.get_running_loop().time())  # TODO: Use a more robust unique identifier in production
    entity_job = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": "TODO: add proper timestamp"  # TODO: Insert actual timestamp
    }

    # Fire and forget the processing task.
    asyncio.create_task(process_entity_task(entity_job, brands_data))

    # Return immediate response including job summary and raw data for prototype purposes.
    return jsonify({
        "message": "Data retrieval initiated successfully",
        "job": entity_job,
        "data": brands_data
    }), 200

@app.route('/brands', methods=['GET'])
async def get_brands():
    global cached_brands
    if cached_brands is None:
        return jsonify({"error": "No data available. Please trigger POST /brands first."}), 404
    return jsonify(cached_brands), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)