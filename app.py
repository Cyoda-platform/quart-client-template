import asyncio
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Local in‑memory job tracker.
entity_job = {}

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
    # Dummy field to satisfy body validation when no fields are provided.
    dummy: str = ""

# Optional: Example function to fetch supplementary data (dummy implementation).
# async def fetch_supplementary_data():
#     await asyncio.sleep(0.1)
#     return {"note": "Supplementary data added asynchronously"}

# Function to create brand item using external service.
# It applies the workflow function and updates the job status accordingly.
async def create_brand_item(job_id, data):
    try:
        # Call add_item with the workflow function that will process the entity before persisting.
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=data,  # raw external data
            )
        entity_job[job_id]["status"] = "success"
        entity_job[job_id]["id"] = item_id
    except Exception as e:
        # Prevent potential infinite recursion by ensuring workflow function is not re-triggered.
        entity_job[job_id]["status"] = "error"
        entity_job[job_id]["message"] = f"Error persisting brand: {str(e)}"

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    # Используем payload вместо data
    # Генерируем уникальный job_id и далее логика остается без изменений.
    job_id = str(datetime.utcnow().timestamp())
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                'https://api.practicesoftwaretesting.com/brands',
                headers={'accept': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    api_data = await resp.json()
                    asyncio.create_task(create_brand_item(job_id, api_data))
                else:
                    entity_job[job_id]["status"] = "error"
                    return jsonify({
                        "status": "error",
                        "message": f"Failed to fetch brand data: HTTP {resp.status}"
                    }), resp.status
        except Exception as e:
            entity_job[job_id]["status"] = "error"
            return jsonify({
                "status": "error",
                "message": f"Exception during data retrieval: {str(e)}"
            }), 500
    return jsonify({
        "status": "success",
        "message": "External data retrieved. Entity processing initiated.",
        "jobId": job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve persisted brands using the entity_service.
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        if items:
            return jsonify(items)
        else:
            return jsonify({
                "status": "error",
                "message": "No brand data available. Please trigger data fetching."
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error retrieving brands: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)