# entity/prototype.py
import asyncio
import datetime
import logging
import aiohttp

from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For GET requests with querystring, use validate_querystring if needed.

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize the schema (data validations are dynamic)

# Startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dummy dataclass for POST request validation in /brands/fetch.
@dataclass
class FetchBrandsRequest:
    # Dummy field; TODO: Add actual fields if parameters are needed.
    dummy: str = ""

EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/brands"

async def process_brands():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as response:
                if response.status != 200:
                    logging.error(f"External API returned status {response.status}")
                    return None

                external_data = await response.json()
                # Additional calculations or data transformations can be added here.
                processed_data = external_data

                # Persist the processed data via the external entity_service.
                item_id = await entity_service.add_item(
                    token=cyoda_token,
                    entity_model="brands",
                    entity_version=ENTITY_VERSION,  # always use this constant
                    entity=processed_data  # the validated data object
                )
                return item_id

    except Exception as e:
        logging.exception("Error processing brands")
        return None

# For POST endpoints, due to an issue in Quart Schema, the @validate_request decorator is placed after the route decorator.
@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)  # Workaround: For POST, validator decorator goes after route decorator.
async def fetch_brands(data: FetchBrandsRequest):
    # Trigger external processing and storage.
    item_id = await process_brands()

    if item_id is None:
        response = {
            "success": False,
            "message": "Failed to fetch or process external source data."
        }
        status_code = 500
    else:
        response = {
            "success": True,
            "id": item_id,
            "message": "External source data fetched and stored successfully."
        }
        status_code = 200

    return jsonify(response), status_code

# GET /brands retrieves data via the external entity_service.
@app.route('/brands', methods=['GET'])
async def get_brands():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION
    )
    if not items:
        response = {
            "data": [],
            "message": "No data available. Please trigger data fetching via POST /brands/fetch"
        }
        status_code = 404
    else:
        response = {
            "data": items
        }
        status_code = 200

    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)