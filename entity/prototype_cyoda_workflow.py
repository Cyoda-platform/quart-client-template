#!/usr/bin/env python3
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request as per quart-schema workaround
import aiohttp
import asyncio
from datetime import datetime

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token  # external service and token

app = Quart(__name__)
QuartSchema(app)

# Startup initialization
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        # Log startup error and raise to prevent running in faulty state.
        print(f"Failed to initialize cyoda: {e}")
        raise e

# Data class for POST request validation
@dataclass
class BrandRequest:
    filter: str = None  # Optional filter parameter; adjust fields as requirements are clarified.

# Workflow function applied to 'brands' entity asynchronously before persistence.
# This function takes the fetched entity data as its only argument and applies modifications.
async def process_brands(entity: dict) -> dict:
    try:
        # Add a processing timestamp to the entity
        entity["processed_at"] = datetime.utcnow().isoformat()
        # Optionally modify entity based on request parameters or other internal logic.
        # E.g., apply transformation if 'filter' key exists.
        if "filter" in entity and entity["filter"]:
            entity["filtered"] = True

        # Fire-and-forget asynchronous task: notify an external analytics or logging service.
        asyncio.create_task(notify_analytics(entity))
    except Exception as proc_ex:
        # Log any processing errors, but do not halt the persistence
        print(f"Error in process_brands workflow: {proc_ex}")
    return entity

# Example of an asynchronous fire-and-forget function.
async def notify_analytics(entity: dict):
    try:
        async with aiohttp.ClientSession() as session:
            # Simulate an asynchronous POST request to an external analytics service.
            async with session.post(
                "https://api.analyticsservice.com/track",
                json={"event": "brand_processed", "data": entity},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    # Log non-successful analytics notifications.
                    print(f"Analytics service responded with status {resp.status}")
    except Exception as ex:
        # Log exception for analytics without impacting main workflow.
        print(f"Analytics notification failed: {ex}")

# Function that fetches raw brand data and stores it using the entity_service.
async def process_entity(params: dict) -> str:
    # Using a timeout to prevent hanging requests
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                    except Exception as json_ex:
                        raise Exception(f"Failed to parse JSON: {json_ex}") from json_ex
                    # All entity specific logic such as transformations or asynchronous tasks
                    # is moved into the workflow function (process_brands).
                    item_id = await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,  # always use this constant
                        entity=data,  # the raw data fetched
                        workflow=process_brands  # workflow function applied to the entity
                    )
                    return item_id
                else:
                    raise Exception(f"Failed to fetch data, status code {resp.status}")
    except Exception as e:
        print(f"Error in process_entity: {e}")
        raise e

@app.route('/api/brands', methods=['POST'])
@validate_request(BrandRequest)  # For POST, validation decorator goes after the route decorator.
async def fetch_and_process_brands(data: BrandRequest):
    req_params = data.__dict__
    try:
        # Delegate core business logic to process_entity, keeping endpoint lean.
        item_id = await process_entity(req_params)
        response = {
            "status": "success",
            "jobId": item_id  # Expose the generated id for tracking purposes.
        }
    except Exception as e:
        # Provide appropriate error details for debugging.
        response = {
            "status": "failed",
            "error": str(e)
        }
    return jsonify(response)

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve stored brands via the external entity_service.
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
        response = {"data": data}
    except Exception as e:
        response = {
            "status": "failed",
            "error": str(e)
        }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)