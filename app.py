import asyncio
import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from pydantic import BaseModel, Field
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.grpc_client.grpc_client import grpc_stream
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
    try:
        await app.background_task
    except asyncio.CancelledError:
        pass

class FetchBrandsRequest(BaseModel):
    fetch_type: str = Field(..., alias="fetchType")

@app.route('/fetch-brands', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    try:
        # Если fetch_type равен "string", возвращаем статический список брендов
        if data.fetch_type == "string":
            brands = ["Brand A", "Brand B", "Brand C"]
            return jsonify({"brands": brands})
        else:
            # В противном случае инициируем процесс извлечения брендов через внешнее API
            job_id = "job_placeholder"
            requested_at = datetime.datetime.utcnow()
            entity_job = {
                job_id: {
                    "status": "processing",
                    "requestedAt": requested_at.isoformat()
                }
            }
            asyncio.create_task(process_entity(entity_job, job_id))
            return jsonify({
                "message": "Brands fetching initiated.",
                "job": entity_job[job_id]
            })
    except Exception as e:
        app.logger.error(f"Error processing request /fetch-brands: {e}")
        return jsonify({"error": "Internal server error"}), 500

async def process_entity(entity_job, job_id):
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    headers = {'accept': 'application/json'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        entity_job[job_id]["status"] = "failed"
                        app.logger.error("Fetched data is not a list.")
                        return
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=item,
                        )
                    entity_job[job_id]["status"] = "completed"
                else:
                    entity_job[job_id]["status"] = "failed"
                    app.logger.error(f"External API returned non-200 status: {response.status}")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        app.logger.error(f"Error processing entity job {job_id}: {e}")

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        if items:
            return jsonify(items)
        else:
            return jsonify({"message": "No brands found."})
    except Exception as e:
        app.logger.error(f"Error fetching brands: {e}")
        return jsonify({"message": "An error occurred while fetching brands."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000)
