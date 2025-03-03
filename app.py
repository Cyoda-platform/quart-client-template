from common.grpc_client.grpc_client import grpc_stream
import asyncio
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)

# Use "job_report" as the entity_model name in all external service calls.
@dataclass
class JobRequest:
    recipient: str  # Use only primitive types

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# The controller now only creates the base entity and passes it to the workflow.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    recipient = data.recipient
    if not recipient:
        return jsonify({"error": "Recipient email is required"}), 400

    # Create a minimal job_report entity with initial details.
    job_report = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "recipient": recipient
    }

    # Pass the workflow function; it will process the entity asynchronously before persistence.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job_report",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_report,  # the validated data object including initial job details
        )
    return jsonify({"id": job_id}), 200

@app.route("/report/<job_id>", methods=["GET"])
async def get_report(job_id):
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="job_report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)