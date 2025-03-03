from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

# Import external service and config constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Startup: initialize cyoda before serving requests
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Dummy schema for POST /job request.
@dataclass
class JobRequest:
    dummy: str = ""  # Placeholder: update as needed

# POST endpoint: Create a new job record.
# The workflow function process_report is applied asynchronously to the entity
# before persistence, offloading the business logic from the controller.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    # Build initial job record with status "received".
    requested_at = datetime.utcnow().isoformat()
    job_data = {"status": "received", "requestedAt": requested_at}
    try:
        # Add new job via external entity_service.
        # The workflow function (process_report) will update the entity
        # with conversion rates, timestamp, and trigger email sending.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            )
    except Exception as e:
        logger.exception("Failed to create job record")
        abort(500, description="Could not create job record.")
    # Return the generated job id; full report details can be retrieved later.
    return jsonify({
        "report_id": job_id,
        "message": "Job created. Retrieve result later using the report endpoint."
    })

# GET endpoint: Retrieve the completed report using the job id.
@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id: str):
    try:
        report = await entity_service.get_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        logger.exception("Error retrieving report")
        abort(500, description="Error retrieving report.")
    # Ensure report exists and is completed.
    if not report or report.get("status") != "completed":
        abort(404, description="Report not found or not completed yet.")
    return jsonify({
        "report_id": report.get("report_id"),
        "btc_usd": report.get("btc_usd"),
        "btc_eur": report.get("btc_eur"),
        "timestamp": report.get("timestamp")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)