from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
import asyncio
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # Also support for validate_querystring if needed

app = Quart(__name__)
QuartSchema(app)

# Startup hook to initialize cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class BrandsRequest:
    # Dummy field for validation. Extend with filtering options as needed.
    filter: str = ""  # Use only primitives

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

# POST endpoint for ingesting brands data
@app.route('/brands', methods=['POST'])
@validate_request(BrandsRequest)  # Workaround: POST validate_request must come after @app.route
async def post_brands(data: BrandsRequest):
    # The validated request data is contained in "data" (e.g., filtering options)
    # Trigger external API call to fetch brands data
    brands_data = await fetch_brands()
    if brands_data is None:
        return jsonify({"error": "Failed to fetch brands data"}), 500

    # Process the raw data
    processed_data = await process_entity(brands_data)

    # Persist the processed data via the external entity_service
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=processed_data  # the validated data object
    )

    # Return the resulting identifier (the full data can be retrieved later via GET endpoint)
    return jsonify({
        "id": new_id,
        "message": "Data ingestion initiated successfully"
    }), 200

# GET endpoint for retrieving persisted brands data
@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve all items of model "brands" from the external service
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION
    )
    if not items:
        return jsonify({"error": "No data available. Please trigger POST /brands first."}), 404
    return jsonify(items), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)