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

@dataclass
class CatRequest:
    type: str = "fact"  # Optional, default to "fact"

# In-memory store for results: resultId -> result data
entity_job = {}

CATS_FACT_API = "https://catfact.ninja/fact"
CATS_IMAGE_API = "https://api.thecatapi.com/v1/images/search"

# Helper: Fetch cat fact
async def fetch_cat_fact(client: httpx.AsyncClient):
    try:
        response = await client.get(CATS_FACT_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("fact")
    except Exception as e:
        logger.exception(e)
        return None

# Helper: Fetch cat image URL
async def fetch_cat_image(client: httpx.AsyncClient):
    try:
        response = await client.get(CATS_IMAGE_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("url")
        return None
    except Exception as e:
        logger.exception(e)
        return None

# Processing task: fetch cat data, combine with "Hello World", store result
async def process_entity(job_id: str, request_data: dict):
    try:
        async with httpx.AsyncClient() as client:
            cat_fact = None
            cat_image = None

            type_requested = request_data.get("type", "fact")

            if type_requested == "fact":
                cat_fact = await fetch_cat_fact(client)
            elif type_requested == "image":
                cat_image = await fetch_cat_image(client)
            elif type_requested == "mixed":
                # fetch both
                cat_fact, cat_image = await asyncio.gather(
                    fetch_cat_fact(client), fetch_cat_image(client)
                )
            else:
                # Unknown type requested — fallback to fact
                cat_fact = await fetch_cat_fact(client)

            # Compose result content
            content = {
                "helloWorldMessage": "Hello World",
                "catData": {}
            }
            if cat_fact:
                content["catData"]["fact"] = cat_fact
            if cat_image:
                content["catData"]["imageUrl"] = cat_image

            # Store result with timestamp
            entity_job[job_id]["status"] = "completed"
            entity_job[job_id]["result"] = {
                "resultId": job_id,
                "content": content,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            logger.info(f"Job {job_id} completed and result stored.")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["result"] = {
            "error": "Failed to process request."
        }

@app.route("/api/cats/hello-world", methods=["POST"])
@validate_request(CatRequest)  # Validation last in POST method (issue workaround)
async def post_hello_world(data: CatRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None
    }

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data.__dict__))

    return jsonify({
        "status": "success",
        "message": "Hello World with cat data fetching started",
        "resultId": job_id
    }), 202

@app.route("/api/cats/result/<result_id>", methods=["GET"])
# No validation needed for GET without parameters
async def get_result(result_id):
    job = entity_job.get(result_id)
    if not job:
        return jsonify({"error": "Result not found"}), 404

    if job["status"] == "processing":
        return jsonify({"status": "processing"}), 202

    if job["status"] == "failed":
        return jsonify({"status": "failed", "error": job["result"].get("error")}), 500

    return jsonify(job["result"]), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
