```python
import asyncio
import datetime
import logging
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache for prototype persistence
entity_job: Dict[str, Dict] = {}
results_cache: Dict[str, Dict] = {}
feedback_cache: Dict[str, Dict] = {}


async def fetch_external_data(input_data: dict) -> dict:
    """
    Example external API call using httpx.AsyncClient.
    This prototype uses a public API to simulate external data retrieval.
    TODO: Replace with your actual external API logic and URL.
    """
    url = "https://api.agify.io"  # Public API that estimates age by name
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

        # Fetch external data
        external_data = await fetch_external_data(input_data)

        # TODO: Add any specific calculations or business logic here.
        # For prototype, combine input_data and external_data as processedResult:
        processed_result = {
            "input": input_data,
            "externalData": external_data,
            "calculatedValue": external_data.get("age", None)  # Example calculation
        }

        # Save processed result
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
async def process_data():
    """
    POST /process-data
    Accept input data, invoke external data sources, perform calculations, return job status.
    """
    data = await request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON body"}), 400

    job_id = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    requested_at = datetime.datetime.utcnow().isoformat()

    entity_job[job_id] = {"status": "queued", "requestedAt": requested_at}

    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, data))

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
async def submit_feedback():
    """
    POST /submit-feedback
    Accept user feedback related to processed results or app experience.
    """
    data = await request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON body"}), 400

    result_id = data.get("resultId")
    feedback_text = data.get("feedback")

    if not result_id or not feedback_text:
        return jsonify({"status": "error", "message": "Missing 'resultId' or 'feedback' fields"}), 400

    # Save feedback in cache with timestamp
    feedback_cache[result_id] = {
        "feedback": feedback_text,
        "submittedAt": datetime.datetime.utcnow().isoformat()
    }

    logger.info(f"Feedback received for resultId={result_id}")

    return jsonify({"status": "success", "message": "Feedback received"})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```