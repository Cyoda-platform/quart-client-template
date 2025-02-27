from datetime import datetime
import asyncio
import aiohttp
import uuid
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Import validate_request

from common.config.config import ENTITY_VERSION  # import constant
from app_init.app_init import cyoda_token, entity_service  # import entity_service and token
from common.repository.cyoda.cyoda_init import init_cyoda  # import init function

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data class for validating POST request body for /api/brands/fetch
@dataclass
class FetchRequest:
    force_refresh: bool = False

# For POST endpoints, the route decorator comes first followed by the validate_request decorator.
# This is a workaround for an issue in the Quart Schema library.

@app.route('/api/brands/fetch', methods=['POST'])
@validate_request(FetchRequest)  # Validate request body after route decorator for POST endpoints
async def fetch_brands(data: FetchRequest):
    force_refresh = data.force_refresh

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.practicesoftwaretesting.com/brands", headers={"accept": "application/json"}) as resp:
                if resp.status != 200:
                    # TODO: Add better error handling and logging as needed.
                    return jsonify({"status": "error", "message": "Failed to fetch brand data from external API"}), resp.status
                external_data = await resp.json()
    except Exception as e:
        # TODO: Enhance exception handling based on actual failure modes.
        return jsonify({"status": "error", "message": "Exception occurred while fetching data", "detail": str(e)}), 500

    # Instead of processing and updating an in-memory cache, add the fetched data as a new entity item.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=external_data  # the validated data object (external data)
    )

    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated. Data added with external service.",
        "job_id": new_id,
        "data_count": len(external_data)  # number of brands processed
    })

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # Retrieve brand data from the external service
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)