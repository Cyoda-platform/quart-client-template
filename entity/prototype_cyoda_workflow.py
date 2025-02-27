from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
import asyncio
import aiohttp
from dataclasses import dataclass
from datetime import datetime
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # Also support for validate_querystring if needed

app = Quart(__name__)
QuartSchema(app)

# Startup hook to initialize cyoda
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log error if necessary
        print(f"Error during cyoda initialization: {e}")
        raise e

@dataclass
class BrandsRequest:
    # Dummy field for validation. Extend with filtering options as needed.
    filter: str = ""  # Use only primitives

async def fetch_brands():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    # Log the non-200 status for debugging
                    print(f"fetch_brands: Received non-200 response: {response.status}")
                    return None
    except asyncio.TimeoutError:
        print("fetch_brands: Request timed out.")
        return None
    except Exception as e:
        print(f"fetch_brands: Unexpected error: {e}")
        return None

async def additional_processing():
    # Example of an additional asynchronous task (fire and forget)
    try:
        # Simulate some fire and forget asynchronous processing (e.g. logging, metrics)
        await asyncio.sleep(0.1)
        # Additional processing logic can be added here
    except Exception as e:
        # Log the error but do not block the main process
        print(f"additional_processing: Error occurred: {e}")

async def fetch_supplementary_data():
    # Fetch supplementary raw data (from a different entity_model) if needed.
    # This function should not interact with the current entity_model to avoid recursion.
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.practicesoftwaretesting.com/supplementary',
                headers={'accept': 'application/json'},
                timeout=10
            ) as response:
                if response.status == 200:
                    supplementary_data = await response.json()
                    return supplementary_data
                else:
                    print(f"fetch_supplementary_data: Received non-200 response: {response.status}")
                    return None
    except Exception as e:
        print(f"fetch_supplementary_data: Error occurred: {e}")
        return None

async def process_brands(entity):
    # Workflow function applied to the entity asynchronously before persistence.
    # Modify entity state directly.
    try:
        # Mark entity as processed and add a timestamp
        entity['processed'] = True
        entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'
        # Optionally update or add additional attributes if missing
        if 'brands' not in entity or not isinstance(entity['brands'], list):
            entity['brands'] = []
        
        # Optionally fetch supplementary data from a different entity_model
        supplementary = await fetch_supplementary_data()
        if supplementary:
            # Store supplementary data in a new key if exists
            entity['supplementary'] = supplementary
        
        # Perform additional asynchronous processing (fire and forget)
        asyncio.create_task(additional_processing())
    except Exception as e:
        print(f"process_brands: Error processing entity: {e}")
    # Return the modified entity which will be persisted.
    return entity

# POST endpoint for ingesting brands data
@app.route('/brands', methods=['POST'])
@validate_request(BrandsRequest)  # Workaround: POST validate_request must come after @app.route
async def post_brands(data: BrandsRequest):
    # The validated request data is contained in "data" (e.g., filtering options)
    # Trigger external API call to fetch brands data
    brands_data = await fetch_brands()
    if brands_data is None:
        return jsonify({"error": "Failed to fetch brands data"}), 500

    try:
        # Persist the raw fetched data via the external entity_service.
        # The workflow function process_brands is applied asynchronously before persistence.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=brands_data,  # raw fetched data
            workflow=process_brands  # Workflow function for additional processing
        )
    except Exception as e:
        print(f"post_brands: Error adding item: {e}")
        return jsonify({"error": "Failed to persist brands data"}), 500

    # Return the resulting identifier (the full data can be retrieved later via GET endpoint)
    return jsonify({
        "id": new_id,
        "message": "Data ingestion initiated successfully"
    }), 200

# GET endpoint for retrieving persisted brands data
@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve all items of model "brands" from the external service
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        print(f"get_brands: Error retrieving brands items: {e}")
        return jsonify({"error": "Failed to retrieve brands data"}), 500

    if not items:
        return jsonify({"error": "No data available. Please trigger POST /brands first."}), 404
    return jsonify(items), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)