from common.grpc_client.grpc_client import grpc_stream
import asyncio
import datetime
import uuid
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

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
    force_refresh: bool = False

@app.route('/brands/fetch', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    # Generate a unique job id and current timestamp
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()

    # Create initial job record state
    job_record = {
        "job_id": job_id,
        "requestedAt": requested_at,
        "status": "processing",
        "brands": []
    }
    # Create job record through entity_service and apply workflow function before persistence.
    created_job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="jobs",
        entity_version=ENTITY_VERSION,
        entity=job_record,
        )
    # Simply return the job id.
    return jsonify({
        "status": "success",
        "message": "Brands fetch job started.",
        "job_id": created_job_id
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve brands cache from external service.
    try:
        brands_items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION
        )
    except Exception:
        # In case of retrieval error, return empty list with error status.
        return jsonify({
            "status": "error",
            "data": []
        })
    return jsonify({
        "status": "success",
        "data": brands_items
    })

if __name__ == '__main__':
    # Run the Quart application.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)