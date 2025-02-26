from common.grpc_client.grpc_client import grpc_stream
import datetime
import asyncio
import aiohttp
import logging
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION  # always use this constant
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)

# Startup initialization for cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
    except Exception as e:
        logger.error(f"Failed to initialize cyoda: {str(e)}")
        raise

# Dummy dataclass for POST /fetch-data request.
@dataclass
class FetchDataRequest:
    # Additional filtering options can be added here.
    filter: str = ""

# External API URLs (constants)
BRANDS_API_URL = "https://api.practicesoftwaretesting.com/brands"
CATEGORIES_API_URL = "https://api.practicesoftwaretesting.com/categories"

async def fetch_external_data(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={'accept': 'application/json'}) as response:
                if response.status != 200:
                    # Handle error responses and log detailed error message.
                    error_text = await response.text()
                    logger.error(f"Failed to fetch data from {url}: {response.status} {error_text}")
                    raise Exception(f"Failed to fetch data from {url}")
                return await response.json()
    except Exception as e:
        logger.error(f"Exception fetching external data from {url}: {str(e)}")
        raise

async def process_data():
    """
    Fetches data from the two external APIs concurrently,
    combines the results with a timestamp, and returns the combined data.
    """
    try:
        # Concurrently fetch brands and categories.
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
        logger.error(f"Error in process_data: {str(e)}")
        raise Exception(f"Error while processing data: {str(e)}")

@app.route('/fetch-data', methods=['POST'])
@validate_request(FetchDataRequest)
async def fetch_data(data: FetchDataRequest):
    """
    POST endpoint to fetch external API data, combine it,
    process it via the workflow function, store it externally,
    and return the item id.
    """
    try:
        # Obtain combined data from external APIs.
        combined_result = await process_data()
        # Store the combined result using the external entity_service.
        # The workflow function applies asynchronous processing before persistence.
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="data_result",
            entity_version=ENTITY_VERSION,
            entity=combined_result,
            )
        logger.info(f"Data stored successfully with id: {item_id}")
        return jsonify({"id": item_id}), 200
    except Exception as e:
        logger.error(f"Error in fetch_data endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/data-result', methods=['GET'])
async def data_result():
    """
    GET endpoint to retrieve stored combined data from the external entity service.
    If no data is available, responds with a 404 status.
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
        logger.error(f"Error in data_result endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)