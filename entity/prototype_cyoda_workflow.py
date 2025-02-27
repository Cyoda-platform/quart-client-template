#!/usr/bin/env python3
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request as per quart-schema workaround
import aiohttp
import asyncio
from uuid import uuid4
from datetime import datetime

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token  # external service and token

app = Quart(__name__)
QuartSchema(app)

# Startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data class for POST request validation
@dataclass
class BrandRequest:
    filter: str = None  # Optional filter parameter; adjust fields as requirements are clarified.

# Workflow function applied to 'brands' entity asynchronously before persistence.
# This function can perform asynchronous operations and update the entity state.
async def process_brands(entity: dict) -> dict:
    # Add a processing timestamp to the entity.
    entity["processed_at"] = datetime.utcnow().isoformat()
    # Fire-and-forget asynchronous task; for example, notify an analytics service.
    # We deliberately do not await this operation since it should not block persistence.
    asyncio.create_task(notify_analytics(entity))
    # Additional business logic can be applied here.
    return entity

# Example of an asynchronous fire-and-forget function.
async def notify_analytics(entity: dict):
    async with aiohttp.ClientSession() as session:
        try:
            # Simulate an asynchronous call to an external analytics service.
            await session.post(
                "https://api.analyticsservice.com/track",
                json={"event": "brand_processed", "data": entity}
            )
        except Exception as ex:
            # Log the exception or handle error as necessary.
            print(f"Analytics notification failed: {ex}")

async def process_entity(params: dict) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # All entity specific logic such as transformations or asynchronous tasks
                    # can be moved to the workflow function (process_brands).
                    item_id = await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,  # always use this constant,
                        entity=data,  # the raw data fetched,
                        workflow=process_brands  # workflow function applied to the entity.
                    )
                    return item_id
                else:
                    raise Exception(f"Failed to fetch data, status code {resp.status}")
        except Exception as e:
            print(f"Error processing entity: {e}")
            raise e

@app.route('/api/brands', methods=['POST'])
@validate_request(BrandRequest)
async def fetch_and_process_brands(data: BrandRequest):
    req_params = data.__dict__
    try:
        # The endpoint remains light as the business logic is delegated to workflow functions.
        item_id = await process_entity(req_params)
        response = {
            "status": "success",
            "jobId": item_id
        }
    except Exception as e:
        response = {
            "status": "failed",
            "error": str(e)
        }
    return jsonify(response)

@app.route('/api/brands', methods=['GET'])
async def get_brands():
    try:
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