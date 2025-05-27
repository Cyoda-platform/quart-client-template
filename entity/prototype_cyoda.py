from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
import httpx

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class HelloRequest:
    action: str  # expects "generate_hello"

async def process_entity(job_id: str, payload: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://httpbin.org/post", json=payload)
            response.raise_for_status()
            # TODO: replace httpbin.org with actual external API or business logic
        # Update the entity job status after processing external logic
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"status": "completed", "message": "Hello World"},
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Processed job {job_id} successfully.")
    except Exception as e:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"status": "failed", "message": None},
            technical_id=job_id,
            meta={}
        )
        logger.exception(f"Failed processing job {job_id}: {e}")

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)
async def post_hello(data: HelloRequest):
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    requested_at = datetime.utcnow().isoformat()
    # Store initial job state in entity_service
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity={"status": "processing", "requestedAt": requested_at, "message": None, "job_id": job_id}
    )
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route("/hello", methods=["GET"])
async def get_hello():
    # Get all items and filter completed with message
    all_jobs = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
    )
    completed_jobs = [
        job for job in all_jobs if job.get("status") == "completed" and job.get("message") is not None
    ]
    if not completed_jobs:
        return jsonify({"message": None, "info": "No completed 'Hello World' message found yet."}), 404
    completed_jobs.sort(key=lambda x: x.get("requestedAt", ""), reverse=True)
    latest = completed_jobs[0]
    return jsonify({"message": latest["message"]})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)