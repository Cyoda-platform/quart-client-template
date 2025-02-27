from common.grpc_client.grpc_client import grpc_stream
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
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

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
                    # Return error if external API call fails.
                    return jsonify({
                        "status": "error",
                        "message": "Failed to fetch brand data from external API"
                    }), resp.status
                external_data = await resp.json()
    except Exception as e:
        # Handle exceptions from the external API call.
        return jsonify({
            "status": "error",
            "message": "Exception occurred while fetching data",
            "detail": str(e)
        }), 500

    # Persist the fetched data. The workflow function process_brands will be invoked
    # asynchronously before the entity is persisted, performing any additional logic.
    try:
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=external_data,  # the entity data fetched from external API
            )
    except Exception as e:
        # Catch any exception that occurs during the persistence process.
        return jsonify({
            "status": "error",
            "message": "Failed to add brand data",
            "detail": str(e)
        }), 500

    return jsonify({
        "status": "success",
        "message": "Brand data fetch initiated. Data added with external service.",
        "job_id": new_id,
        "data_count": len(external_data) if isinstance(external_data, list) else 1
    })

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve brand data from the external service.
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        # Handle errors during data retrieval.
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve brands",
            "detail": str(e)
        }), 500
    return jsonify(items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)