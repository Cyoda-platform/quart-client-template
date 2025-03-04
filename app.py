from common.grpc_client.grpc_client import grpc_stream
import asyncio
import uuid
import logging
import datetime
from typing import List, Dict, Any

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request for POST endpoints
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

# Data class for the analyze request body
@dataclass
class AnalyzeRequest:
    post_ids: List[int]
    email: str

@app.route("/api/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze(data: AnalyzeRequest):
    try:
        post_ids = data.post_ids
        recipient_email = data.email

        if not post_ids or not recipient_email:
            return jsonify({"error": "post_ids and email are required fields"}), 400

        requested_at = datetime.datetime.utcnow().isoformat()
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "post_ids": post_ids,
            "recipient_email": recipient_email
        }

        # The workflow function 'process_job' is applied to the job entity asynchronously before persistence.
        # Any asynchronous tasks (analysis, email sending, etc.) are executed inside the workflow.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,
            )
        logger.info(f"Job {job_id} created with post_ids {post_ids} for recipient {recipient_email}")

        # The analysis is processed within the workflow,
        # so we can immediately return the final status of the job entity.
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        return jsonify({"job_id": job_id, "status": job.get("status"), "report": job.get("report", "")}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/result/<job_id>", methods=["GET"])
async def get_result(job_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
        if not job:
            return jsonify({"error": "Job not found"}), 404
        response = {
            "job_id": job_id,
            "status": job.get("status"),
            "report": job.get("report", "")
        }
        return jsonify(response), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)