from common.grpc_client.grpc_client import grpc_stream
import asyncio
import aiohttp
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class FetchBrandsRequest:
    fetch_mode: str = None  # Optional parameter for future use

@app.route('/fetch-brands', methods=['POST'])
@validate_request(FetchBrandsRequest)  # Validation decorator must be placed after the route decorator.
async def fetch_brands(data: FetchBrandsRequest):
    try:
        # Fetch data from the external API.
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status != 200:
                    logger.error("External API responded with status %s", resp.status)
                    return jsonify({"error": "Failed to fetch external data."}), 500
                external_data = await resp.json()
    except Exception as e:
        logger.exception("Exception during external API call")
        return jsonify({"error": str(e)}), 500

    try:
        # Persist the fetched data with the workflow function applied.
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # Always use this constant
            entity=external_data,           # Validated external data
            )
    except Exception as e:
        logger.exception("Exception during persisting entity")
        return jsonify({"error": "Failed to store entity data."}), 500

    return jsonify({
        "id": item_id,
        "message": "Data fetched and stored successfully."
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve processed brand data from the external entity service.
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(data)
    except Exception as e:
        logger.exception("Exception fetching brand data")
        return jsonify({"error": "Failed to retrieve brand data."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)