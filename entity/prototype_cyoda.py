from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request  # validate_querystring exists but not needed for /data-result
import aiohttp
import asyncio
import datetime
import json
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION  # always use this constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Startup initialization for cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dummy dataclass for POST /fetch-data request.
@dataclass
class FetchDataRequest:
    # TODO: Add request parameters if needed for filtering or additional options.
    filter: str = ""

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
    combines the results with a timestamp, and returns the combined data.
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
        return combined_result

    except Exception as e:
        # TODO: Improve error handling and logging as needed
        raise Exception(f"Error while processing data: {str(e)}")

# For POST endpoints, per the workaround issue with quart_schema, route decorator is first, validate_request second.
@app.route('/fetch-data', methods=['POST'])
@validate_request(FetchDataRequest)  # NOTE: This is placed after route decorator as workaround for POST requests.
async def fetch_data(data: FetchDataRequest):
    """
    POST endpoint to fetch external API data, combine it, store it externally,
    and return the item id.
    """
    try:
        # Process the external API data and combine it.
        combined_result = await process_data()
        # Store the combined result using the external entity_service.
        # The entity_model is set to "data_result", adjust if needed.
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="data_result",
            entity_version=ENTITY_VERSION,
            entity=combined_result
        )
        # Return the generated id; the result should be retrieved via a separate GET endpoint.
        return jsonify({"id": item_id}), 200

    except Exception as e:
        # Return error response with a 500 status code.
        return jsonify({"error": str(e)}), 500

# GET endpoint to retrieve the stored combined data.
@app.route('/data-result', methods=['GET'])
async def data_result():
    """
    GET endpoint to retrieve stored combined data from the external entity service.
    It calls get_items to retrieve all stored items of model 'data_result'.
    """
    try:
        results = await entity_service.get_items(
            token=cyoda_token,
            entity_model="data_result",
            entity_version=ENTITY_VERSION
        )
        if not results:
            abort(404, description="No combined data available")
        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)