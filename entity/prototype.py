import asyncio
import datetime
import json

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for persistence (mock persistence)
CACHE = {}

# External API URLs (constants)
BRANDS_API_URL = "https://api.practicesoftwaretesting.com/brands"
CATEGORIES_API_URL = "https://api.practicesoftwaretesting.com/categories"


async def fetch_external_data(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={'accept': 'application/json'}) as response:
            if response.status != 200:
                # TODO: Handle specific error logic or retries if required
                raise Exception(f"Failed to fetch data from {url}")
            return await response.json()


async def process_data():
    """
    Fetches data from the two external APIs concurrently,
    combines the results with a timestamp, and stores it in CACHE.
    """
    try:
        # Fetch brands and categories concurrently
        brands_task = asyncio.create_task(fetch_external_data(BRANDS_API_URL))
        categories_task = asyncio.create_task(fetch_external_data(CATEGORIES_API_URL))
        brands, categories = await asyncio.gather(brands_task, categories_task)

        combined_at = datetime.datetime.utcnow().isoformat() + "Z"
        combined_result = {
            "brands": brands,
            "categories": categories,
            "combined_at": combined_at
        }

        # Store the combined result in the local cache
        CACHE["data_result"] = combined_result
        return combined_result

    except Exception as e:
        # TODO: Improve error handling and logging as needed
        raise Exception(f"Error while processing data: {str(e)}")


@app.route('/fetch-data', methods=['POST'])
async def fetch_data():
    """
    POST endpoint to fetch external API data, combine it, store it locally,
    and return the combined data.
    """
    # TODO: Process additional request filters if provided in request.json
    try:
        # Using a fire-and-forget pattern if processing in background is desired:
        # job_id = "some_unique_id"  # TODO: generate unique job id if needed
        # entity_job[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat() + "Z"}
        # asyncio.create_task(process_entity(entity_job, request_json))

        # For this prototype, we await the processing task directly.
        combined_result = await process_data()
        return jsonify(combined_result), 200

    except Exception as e:
        # Return error response with a 500 status code.
        return jsonify({"error": str(e)}), 500


@app.route('/data-result', methods=['GET'])
async def data_result():
    """
    GET endpoint to retrieve the stored combined data.
    """
    result = CACHE.get("data_result")
    if result is None:
        # No data available yet.
        abort(404, description="No combined data available")
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)