from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: due to quart-schema defect, place validate_querystring before @app.route for GET,
# and validate_request after @app.route for POST.

@dataclass
class HelloRequest:
    action: str  # expects "generate_hello"

# In-memory cache for job state
entity_job: Dict[str, Dict] = {}

async def process_entity(job_id: str, payload: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://httpbin.org/post", json=payload)
            response.raise_for_status()
            # TODO: replace httpbin.org with actual external API or business logic
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["message"] = "Hello World"
        logger.info(f"Processed job {job_id} successfully.")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["message"] = None
        logger.exception(f"Failed processing job {job_id}: {e}")

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)  # validation last for POST due to library defect
async def post_hello(data: HelloRequest):
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    requested_at = datetime.utcnow()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at, "message": None}
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

@app.route("/hello", methods=["GET"])
async def get_hello():
    completed_jobs = [
        (jid, info)
        for jid, info in entity_job.items()
        if info["status"] == "completed" and info["message"] is not None
    ]
    if not completed_jobs:
        return jsonify({"message": None, "info": "No completed 'Hello World' message found yet."}), 404
    completed_jobs.sort(key=lambda x: x[1]["requestedAt"], reverse=True)
    latest = completed_jobs[0][1]
    return jsonify({"message": latest["message"]})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)