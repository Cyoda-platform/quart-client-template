from dataclasses import dataclass
import asyncio
import datetime
import logging
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class ProcessDataRequest:
    inputData: Dict[str, Any]

@dataclass
class FeedbackRequest:
    resultId: str
    feedback: str

# In-memory local cache for prototype persistence
entity_job: Dict[str, Dict[str, Any]] = {}
results_cache: Dict[str, Dict[str, Any]] = {}
feedback_cache: Dict[str, Dict[str, Any]] = {}

async def fetch_external_data(input_data: dict) -> dict:
    """
    Example external API call using httpx.AsyncClient.
    TODO: Replace with your actual external API logic and URL.
    """
    url = "https://api.agify.io"
    params = {"name": input_data.get("name", "default")}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"External API response: {data}")
            return data
    except httpx.HTTPError as e:
        logger.exception(f"External API call failed: {e}")
        return {}

async def process_entity(job_id: str, input_data: dict):
    """
    Process the entity: call external API, do calculations, update job and results cache.
    """
    try:
        entity_job[job_id]["status"] = "processing"
        entity_job[job_id]["startedAt"] = datetime.datetime.utcnow().isoformat()

        external_data = await fetch_external_data(input_data)

        # TODO: Add specific calculations or business logic here.
        processed_result = {
            "input": input_data,
            "externalData": external_data,
            "calculatedValue": external_data.get("age")
        }

        results_cache[job_id] = {
            "resultId": job_id,
            "resultData": processed_result,
            "processedAt": datetime.datetime.utcnow().isoformat()
        }

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        logger.exception(f"Processing job {job_id} failed.")

@app.route("/process-data", methods=["POST"])
# issue workaround: validate_request must come after route for POST
@validate_request(ProcessDataRequest)
async def process_data(data: ProcessDataRequest):
    """
    POST /process-data
    Accept input data, invoke external data sources, perform calculations, return job status.
    """
    input_data = data.inputData
    job_id = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    requested_at = datetime.datetime.utcnow().isoformat()

    entity_job[job_id] = {"status": "queued", "requestedAt": requested_at}

    asyncio.create_task(process_entity(job_id, input_data))

    return jsonify({
        "status": "accepted",
        "jobId": job_id,
        "message": "Processing started"
    })

@app.route("/results/<string:result_id>", methods=["GET"])
async def get_results(result_id):
    """
    GET /results/{resultId}
    Retrieve processed results by resultId.
    """
    result = results_cache.get(result_id)
    if not result:
        return jsonify({"status": "error", "message": "Result not found"}), 404
    return jsonify(result)

@app.route("/submit-feedback", methods=["POST"])
# issue workaround: validate_request must come after route for POST
@validate_request(FeedbackRequest)
async def submit_feedback(data: FeedbackRequest):
    """
    POST /submit-feedback
    Accept user feedback related to processed results or app experience.
    """
    result_id = data.resultId
    feedback_text = data.feedback

    feedback_cache[result_id] = {
        "feedback": feedback_text,
        "submittedAt": datetime.datetime.utcnow().isoformat()
    }

    logger.info(f"Feedback received for resultId={result_id}")

    return jsonify({"status": "success", "message": "Feedback received"})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)