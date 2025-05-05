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

# In-memory cache for jobs
entity_job = {}

@dataclass
class ProcessDataRequest:
    postId: str  # expecting postId as string for external API param

async def fetch_external_data(some_param: str) -> dict:
    """
    Example external API call.
    Using a real public API for demonstration: JSONPlaceholder posts.
    TODO: Replace with real business external API and parameters.
    """
    url = f"https://jsonplaceholder.typicode.com/posts/{some_param}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch external data: {e}")
            return {}

async def process_entity(job_id: str, input_data: dict):
    """
    Perform business logic:
    - Fetch external data (mocked here with JSONPlaceholder)
    - Perform simple calculation (count number of words in title + body)
    - Store results in entity_job cache
    """
    try:
        logger.info(f"Start processing job {job_id}")
        post_id = str(input_data.get("postId", "1"))  # default to "1" if missing

        external_data = await fetch_external_data(post_id)
        if not external_data:
            entity_job[job_id]["status"] = "failed"
            entity_job[job_id]["message"] = "Failed to retrieve external data"
            return

        title = external_data.get("title", "")
        body = external_data.get("body", "")
        word_count = len((title + " " + body).split())

        result = {
            "externalData": external_data,
            "wordCount": word_count,
        }

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = result
        logger.info(f"Completed job {job_id}")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["message"] = "Internal processing error"

@app.route("/process-data", methods=["POST"])
@validate_request(ProcessDataRequest)  # validation last in post method (issue workaround)
async def process_data(data: ProcessDataRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "message": None,
        "result": None,
    }

    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id, data.__dict__))

    return jsonify({"processId": job_id, "status": "processing"}), 202

@app.route("/results/<process_id>", methods=["GET"])
# validation first in get method (issue workaround)
async def get_results(process_id):
    job = entity_job.get(process_id)
    if not job:
        return jsonify({"message": "processId not found"}), 404

    resp = {
        "processId": process_id,
        "status": job["status"],
        "result": job.get("result"),
        "message": job.get("message"),
    }
    return jsonify(resp), 200

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
