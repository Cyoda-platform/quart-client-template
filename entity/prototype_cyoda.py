from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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
    - Store results in entity_service
    """
    try:
        logger.info(f"Start processing job {job_id}")
        post_id = str(input_data.get("postId", "1"))  # default to "1" if missing

        external_data = await fetch_external_data(post_id)
        if not external_data:
            # Update job status to failed in entity_service
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity={
                    "status": "failed",
                    "message": "Failed to retrieve external data",
                    "result": None,
                    "requestedAt": None,
                },
                meta={},
            )
            return

        title = external_data.get("title", "")
        body = external_data.get("body", "")
        word_count = len((title + " " + body).split())

        result = {
            "externalData": external_data,
            "wordCount": word_count,
        }

        # Update job status to completed in entity_service
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={
                "status": "completed",
                "message": None,
                "result": result,
                "requestedAt": None,
            },
            meta={},
        )
        logger.info(f"Completed job {job_id}")
    except Exception as e:
        logger.exception(e)
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={
                "status": "failed",
                "message": "Internal processing error",
                "result": None,
                "requestedAt": None,
            },
            meta={},
        )

@app.route("/process-data", methods=["POST"])
@validate_request(ProcessDataRequest)  # validation last in post method (issue workaround)
async def process_data(data: ProcessDataRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    # Add initial job record to entity_service
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity={
            "status": "processing",
            "requestedAt": requested_at,
            "message": None,
            "result": None,
            "technical_id": job_id,  # store id in entity if needed, though id is managed externally
        },
    )
    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id, data.__dict__))

    return jsonify({"processId": job_id, "status": "processing"}), 202

@app.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=process_id,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "processId not found"}), 404

    if not job:
        return jsonify({"message": "processId not found"}), 404

    resp = {
        "processId": process_id,
        "status": job.get("status"),
        "result": job.get("result"),
        "message": job.get("message"),
    }
    return jsonify(resp), 200

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)