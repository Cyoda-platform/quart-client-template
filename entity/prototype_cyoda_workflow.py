from dataclasses import dataclass
import logging
from datetime import datetime

from quart import Quart, jsonify
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

# Workflow function for entity_job - runs BEFORE persisting the entity
async def process_entity_job(entity: dict):
    job_id = entity.get("job_id")
    if not job_id:
        logger.error("Job ID missing from entity in workflow.")
        entity["status"] = "failed"
        entity["message"] = "Missing job_id"
        return entity

    try:
        # Perform external async operation
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post("https://httpbin.org/post", json=entity)
            response.raise_for_status()
        # Update entity state directly (mutation)
        entity["status"] = "completed"
        entity["message"] = "Hello World"
        logger.info(f"Job {job_id} processed successfully in workflow.")
    except Exception as e:
        entity["status"] = "failed"
        entity["message"] = None
        logger.exception(f"Job {job_id} failed in workflow: {e}")

    return entity

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)
async def post_hello(data: HelloRequest):
    # Validate action explicitly
    if data.action != "generate_hello":
        return jsonify({"error": "Invalid action"}), 400

    job_id = datetime.utcnow().isoformat(timespec='milliseconds') + "-" + str(id(data))
    requested_at = datetime.utcnow().isoformat(timespec='milliseconds')

    initial_entity = {
        "status": "processing",
        "requestedAt": requested_at,
        "message": None,
        "job_id": job_id,
    }

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
            workflow=process_entity_job
        )
    except Exception as e:
        logger.exception(f"Failed to add entity_job: {e}")
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route("/hello", methods=["GET"])
async def get_hello():
    try:
        all_jobs = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(f"Failed to get entity_jobs: {e}")
        return jsonify({"error": "Internal server error"}), 500

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