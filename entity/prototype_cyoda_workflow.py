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
async def process_brands(entity: dict) -> dict:
    # Modify the entity data before it is persisted.
    # For example, add a processed timestamp.
    entity["processed_at"] = datetime.utcnow().isoformat()
    # Additional processing logic can be added here.
    return entity

async def process_entity(params: dict) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Apply additional business logic or calculations if required.
                    # Store the processed data using the external entity_service with a workflow function.
                    item_id = await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,  # always use this constant,
                        entity=data,  # the processed data object,
                        workflow=process_brands  # workflow function applied to the entity.
                    )
                    return item_id
                else:
                    # Handle error response properly.
                    raise Exception(f"Failed to fetch data, status code {resp.status}")
        except Exception as e:
            # Handle exception properly (e.g., logging the error details).
            print(f"Error processing entity: {e}")
            raise e

@app.route('/api/brands', methods=['POST'])
@validate_request(BrandRequest)  # For POST, validation decorator goes after the route decorator.
async def fetch_and_process_brands(data: BrandRequest):
    # Access validated request data from the dataclass
    req_params = data.__dict__
    try:
        # Process the brands data and store it via the external entity_service.
        # Just return the id of the stored entity.
        item_id = await process_entity(req_params)
        response = {
            "status": "success",
            "jobId": item_id  # Expose the generated id for tracking purposes.
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
        # Retrieve all stored brands via the external entity_service.
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
        response = {
            "data": data
        }
    except Exception as e:
        response = {
            "status": "failed",
            "error": str(e)
        }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)