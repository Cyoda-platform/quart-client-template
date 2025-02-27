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

# Workflow function applied to the entity asynchronously before persistence.
# This function takes the entity data as the only argument.
# It encapsulates additional asynchronous processing logic that might include fire-and-forget tasks.
async def process_brands(entity_data):
    # Example: Add a processed timestamp to the entity data.
    entity_data['processed_at'] = datetime.utcnow().isoformat() + "Z"

    # Example: Extract a summary (e.g., count of brands) and add it as a supplementary entity.
    # Note: We use a different entity_model ("brands_summary") to avoid recursion.
    if isinstance(entity_data, list):
        summary = {"brand_count": len(entity_data), "logged_at": datetime.utcnow().isoformat() + "Z"}
        # Add supplementary entity asynchronously (fire-and-forget style).
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands_summary",
            entity_version=ENTITY_VERSION,
            entity=summary,
            workflow=None  # No workflow for supplementary entity
        )

    # Additional asynchronous tasks can be invoked here.
    await asyncio.sleep(0)  # Placeholder for async operations

# Data class for validating POST request body for /api/brands/fetch
@dataclass
class FetchRequest:
    force_refresh: bool = False

# The endpoint remains thin, deferring processing logic to the workflow function.
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

    # Persist the fetched data. The workflow function process_brands will be invoked
    # asynchronously before the entity is persisted, performing any additional logic.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=external_data,  # the entity data fetched from external API
        workflow=process_brands  # Workflow function applied to the entity before persistence.
    )

    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated. Data added with external service.",
        "job_id": new_id,
        "data_count": len(external_data) if isinstance(external_data, list) else 0
    })

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    # Retrieve brand data from the external service.
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)