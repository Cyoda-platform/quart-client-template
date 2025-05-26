from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Dataclass for POST /process request validation
@dataclass
class ProcessRequest:
    inputData: dict  # TODO: refine structure if needed

async def call_external_api(input_value: str) -> dict:
    url = "https://api.agify.io"
    params = {"name": input_value}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.exception(f"External API call failed: {e}")
        raise

async def process_entity(job_id: str, input_data: dict):
    try:
        name = input_data.get("name")
        if not name:
            raise ValueError("Missing 'name' in inputData")
        result = await call_external_api(name)
        processed_result = {
            "inputName": name,
            "predictedAge": result.get("age"),
            "count": result.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = processed_result
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        logger.exception(f"Processing failed for job {job_id}: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["message"] = str(e)

entity_jobs = {}

@app.route("/process", methods=["POST"])
# NOTE: validate_request placed after route decorator due to quart-schema defect workaround
@validate_request(ProcessRequest)
async def post_process(data: ProcessRequest):
    try:
        input_data = data.inputData
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat() + "Z"
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
        asyncio.create_task(process_entity(job_id, input_data))
        return jsonify({"processId": job_id, "status": "processing", "message": "Processing started"}), 202
    except Exception as e:
        logger.exception(f"Error in /process endpoint: {e}")
        return jsonify({"message": "Invalid request or internal error"}), 500

@app.route("/result/<process_id>", methods=["GET"])
async def get_result(process_id):
    job = entity_jobs.get(process_id)
    if not job:
        return jsonify({"message": f"Process ID {process_id} not found"}), 404
    response = {"processId": process_id, "status": job.get("status"), "message": job.get("message", "")}
    if job.get("status") == "completed":
        response["result"] = job.get("result")
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)