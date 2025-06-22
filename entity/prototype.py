from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: validate_request must come after @app.route for POST due to quart-schema defect

@dataclass
class ProcessRequest:
    inputData: dict

# POST endpoint: validation last for POST (workaround for quart-schema issue)
@app.route('/process', methods=['POST'])
@validate_request(ProcessRequest)
async def process(data: ProcessRequest):
    input_data = data.inputData

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow()

    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "resultData": None,
        "error": None
    }

    asyncio.create_task(process_entity(entity_jobs, job_id, input_data))

    return jsonify({
        "processId": job_id,
        "status": "processing"
    }), 202

# GET endpoint: no validation needed for path parameters
@app.route('/result/<process_id>', methods=['GET'])
async def get_result(process_id):
    job = entity_jobs.get(process_id)
    if job is None:
        return jsonify({"error": "processId not found"}), 404

    response = {
        "processId": process_id,
        "status": job["status"],
        "resultData": job.get("resultData")
    }
    if job["status"] == "failed":
        response["error"] = job.get("error")

    return jsonify(response)

async def fetch_external_data():
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get("https://icanhazdadjoke.com/", headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("joke", "No joke found")
        except Exception as e:
            logger.exception("Failed to fetch external data")
            raise e

async def process_entity(job_store, job_id, input_data):
    try:
        logger.info(f"Processing job {job_id} with input: {input_data}")

        external_info = await fetch_external_data()

        # TODO: add specific calculations or business logic here
        result_data = {
            "inputReceived": input_data,
            "externalInfo": external_info,
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }

        job_store[job_id].update({
            "status": "completed",
            "resultData": result_data,
            "completedAt": datetime.utcnow()
        })

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        job_store[job_id].update({
            "status": "failed",
            "error": str(e),
            "completedAt": datetime.utcnow()
        })
        logger.exception(f"Job {job_id} failed during processing")

# In-memory mock persistence
entity_jobs = {}

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)