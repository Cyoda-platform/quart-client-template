from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
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
    External API call example.
    """
    url = f"https://jsonplaceholder.typicode.com/posts/{some_param}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch external data: {e}")
            return {}

async def process_entity_job(entity: dict) -> dict:
    """
    Workflow function applied before persisting entity_job.
    Handles async fetching and processing logic.
    Modifies entity dict in place to update state and results.
    """
    logger.info(f"Workflow process_entity_job started for technical_id={entity.get('technical_id')}")

    try:
        # Add requestedAt if missing
        if "requestedAt" not in entity or entity["requestedAt"] is None:
            entity["requestedAt"] = datetime.utcnow().isoformat()

        # Extract postId input parameter from entity or fallback
        input_data = entity.get("inputData", {})
        post_id = str(input_data.get("postId", "1"))

        # Fetch external data async
        external_data = await fetch_external_data(post_id)
        if not external_data:
            entity["status"] = "failed"
            entity["message"] = "Failed to retrieve external data"
            entity["result"] = None
            return entity

        # Perform calculation: count words in title + body
        title = external_data.get("title", "")
        body = external_data.get("body", "")
        word_count = len((title + " " + body).split())

        result = {
            "externalData": external_data,
            "wordCount": word_count,
        }

        # Update entity status and results
        entity["status"] = "completed"
        entity["message"] = None
        entity["result"] = result

        # Example: add supplementary raw data entity of different model
        # For example, store raw external_data as entity_raw_data model with reference to this job
        # Avoid infinite recursion by not modifying current entity_job
        try:
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="entity_raw_data",
                entity_version=ENTITY_VERSION,
                entity={
                    "jobId": entity.get("technical_id"),
                    "rawData": external_data,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to add supplementary entity_raw_data: {e}")

    except Exception as e:
        logger.exception(f"Exception in workflow process_entity_job: {e}")
        entity["status"] = "failed"
        entity["message"] = "Internal processing error"
        entity["result"] = None

    return entity

@app.route("/process-data", methods=["POST"])
@validate_request(ProcessDataRequest)  # validation last in post method (issue workaround)
async def process_data(data: ProcessDataRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    # Initial entity includes inputData so workflow can access original inputs
    initial_entity = {
        "status": "processing",
        "requestedAt": requested_at,
        "message": None,
        "result": None,
        "technical_id": job_id,
        "inputData": data.__dict__,  # pass original inputs for workflow
    }

    # Add item with workflow function which will perform async processing before persistence
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=initial_entity,
        workflow=process_entity_job,
    )

    # No need for explicit asyncio.create_task or background tasks here
    # Workflow handles async processing before persistence

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
        logger.warning(f"Error retrieving process_id {process_id}: {e}")
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