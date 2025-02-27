#!/usr/bin/env python3
import asyncio
import datetime
import logging
import aiohttp

from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Initialize schema for request validations

# Startup initialization
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        logging.exception("Error during startup initialization")


# Dummy dataclass for POST request validation in /brands/fetch.
@dataclass
class FetchBrandsRequest:
    # Dummy field; add actual fields if required.
    dummy: str = ""


EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/brands"

async def async_logging(entity):
    # Fire-and-forget async task example:
    try:
        # Simulate additional asynchronous processing or external notifications.
        await asyncio.sleep(0)
        processed_at = entity.get("workflow_processed_at", "unknown time")
        logging.info(f"Async Log: Entity processed at {processed_at}.")
    except Exception as e:
        logging.exception("Error in async_logging")


async def workflow_brands(entity):
    # Workflow function applied to the entity before persistence.
    try:
        # Add a processing timestamp to the entity.
        entity["workflow_processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        # Example of additional business logic:
        # Validate that certain required fields exist. If not, add defaults.
        if "status" not in entity:
            entity["status"] = "new"
        
        # You can invoke any fire-and-forget asynchronous tasks here.
        asyncio.create_task(async_logging(entity))
        
        # Suppose we want to add supplemental data from an external service,
        # ensure that the external call does not modify the current entity by using
        # a secondary entity_model if needed. (This example is commented out.)
        #
        # supplemental_data = await fetch_supplemental_data()
        # if supplemental_data:
        #     await entity_service.add_item(
        #         token=cyoda_token,
        #         entity_model="brands_supplement",
        #         entity_version=ENTITY_VERSION,
        #         entity=supplemental_data,
        #         workflow=lambda x: x  # No further workflow on supplemental entity.
        #     )
        
    except Exception as e:
        logging.exception("Error in workflow_brands")
    # Return the modified entity, which will be persisted.
    return entity

async def process_brands():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as response:
                if response.status != 200:
                    logging.error(f"External API returned status {response.status}")
                    return None

                try:
                    external_data = await response.json()
                except Exception as je:
                    logging.exception("Error parsing JSON from external API")
                    return None

                # Ensure external_data is a dict; if not, wrap it.
                if not isinstance(external_data, dict):
                    external_data = {"data": external_data}

                # Minimal processing here; heavy lifting can be done in the workflow.
                processed_data = external_data

                # Persist the processed data using entity_service.add_item.
                # The workflow function will be applied to the entity before persistence.
                item_id = await entity_service.add_item(
                    token=cyoda_token,
                    entity_model="brands",
                    entity_version=ENTITY_VERSION,
                    entity=processed_data,
                    workflow=workflow_brands  # Asynchronously modify entity before storage.
                )
                return item_id

    except Exception as e:
        logging.exception("Error in process_brands")
        return None

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    # The controller is kept minimal; business logic is delegated.
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

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logging.exception("Error retrieving brands data")
        return jsonify({
            "data": [],
            "message": "Error retrieving data."
        }), 500

    if not items:
        response = {
            "data": [],
            "message": "No data available. Please trigger data fetching via POST /brands/fetch"
        }
        status_code = 404
    else:
        response = {"data": items}
        status_code = 200
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)