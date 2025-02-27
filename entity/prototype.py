import asyncio
import aiohttp
import datetime
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache for persistence (mock persistence)
BRANDS_CACHE = []


@app.route('/fetch-brands', methods=['POST'])
async def fetch_brands():
    """
    POST /fetch-brands
    Triggers the external API call and fires a background task to process the data.
    """
    # TODO: Generate a unique job_id (using UUID or similar) if required
    job_id = "job_placeholder"

    # Create a simple entity job dict to simulate job processing information
    requested_at = datetime.datetime.utcnow()
    entity_job = {
        job_id: {
            "status": "processing",
            "requestedAt": requested_at.isoformat()
        }
    }

    # Fire and forget the processing task.
    # TODO: If additional processing details are required, update the process_entity accordingly.
    asyncio.create_task(process_entity(entity_job, job_id))

    return jsonify({
        "message": "Brands fetching initiated.",
        "job": entity_job[job_id]
    })


async def process_entity(entity_job, job_id):
    """
    Process the external API call, fetch brands data, and update the in-memory cache.
    This function runs asynchronously in the background.
    """
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    headers = {'accept': 'application/json'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # TODO: Replace this in-memory storage with proper persistence if needed.
                    global BRANDS_CACHE
                    BRANDS_CACHE = data
                    entity_job[job_id]["status"] = "completed"
                else:
                    entity_job[job_id]["status"] = "failed"
                    # TODO: Handle non-200 responses as needed.
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        # TODO: Add logging or error handling here.
        print(f"Error processing entity job {job_id}: {e}")


@app.route('/brands', methods=['GET'])
async def get_brands():
    """
    GET /brands
    Retrieves the list of brands stored from the external API call.
    """
    if BRANDS_CACHE:
        return jsonify(BRANDS_CACHE)
    else:
        return jsonify({"message": "No brands found."})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)