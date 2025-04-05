import asyncio
from datetime import datetime
import logging
from dataclasses import dataclass

from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request
import httpx

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class DataQuery:
    query: str  # Only primitive type is allowed

async def process_entity(job_id: str, query: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://postman-echo.com/post", json={"query": query})
            response.raise_for_status()
            result = response.json()
            update_data = {"status": "completed", "result": result}
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity=update_data,
                meta={}
            )
            logger.info(f"Job {job_id} completed with result: {result}")
    except Exception as e:
        logger.exception(e)
        update_data = {"status": "failed", "error": str(e)}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity=update_data,
            meta={}
        )

@app.route("/hello", methods=["GET"])
async def hello():
    return jsonify({"message": "Hello, World!"}), 200

@app.route("/data", methods=["POST"])
@validate_request(DataQuery)
async def data(data: DataQuery):
    query = data.query
    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "query": query,
        "status": "processing",
        "requestedAt": requested_at,
    }
    # Create a new job record using the external entity_service
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=job_data
    )
    # Start processing the job asynchronously
    asyncio.create_task(process_entity(job_id, query))
    return jsonify({"job_id": job_id, "status": "processing", "requestedAt": requested_at}), 202

@app.route("/job/<job_id>", methods=["GET"])
async def get_job(job_id: str):
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        abort(404, description="Job not found.")
    return jsonify({"job_id": job_id, "job": job}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)