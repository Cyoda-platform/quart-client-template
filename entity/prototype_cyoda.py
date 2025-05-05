from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory storage for workflow jobs status
entity_job: dict = {}

CAT_FACT_API_URL = "https://catfact.ninja/fact"

@dataclass
class EmptyBody:
    pass

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def fetch_cat_fact_from_api() -> Optional[str]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.error("No 'fact' field in Cat Fact API response")
                return None
            return fact
        except Exception as e:
            logger.exception(f"Failed to fetch cat fact from external API: {e}")
            return None

async def process_entity(job_id: str, data: dict):
    """
    Workflow: fetch cat fact and store it via entity_service.
    """
    try:
        entity_job[job_id]["status"] = "fetching"
        fact = await fetch_cat_fact_from_api()
        if not fact:
            entity_job[job_id]["status"] = "failed"
            return

        entity_job[job_id]["status"] = "storing"

        # Create entity data with current timestamp
        now_iso = datetime.utcnow().isoformat() + "Z"
        entity_data = {
            "fact": fact,
            "fetchedAt": now_iso,
        }

        # Add item via entity_service
        entity_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
        )

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["catFactId"] = entity_id

    except Exception as e:
        logger.exception(f"Error processing entity job {job_id}: {e}")
        entity_job[job_id]["status"] = "failed"

# POST endpoint: validation last due to quart-schema issue workaround
@app.route("/catfact/fetch", methods=["POST"])
@validate_request(EmptyBody)  # validate empty JSON body, workaround: validate last for POST
async def fetch_catfact(data: EmptyBody):
    """
    POST endpoint to trigger fetching a new cat fact and storing it.
    Fire-and-forget workflow.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget processing
    asyncio.create_task(process_entity(job_id, {}))

    return jsonify(
        {
            "status": "success",
            "message": "Cat fact fetch job started",
            "jobId": job_id,
        }
    ), 202

# GET endpoint without parameters: get latest cat fact by querying all and selecting latest
@app.route("/catfact/latest", methods=["GET"])
async def get_latest_catfact():
    """
    GET endpoint to retrieve the most recently fetched cat fact.
    """
    try:
        all_items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
        )
        if not all_items:
            return jsonify({"error": "No cat facts stored yet"}), 404

        # Find entity with latest fetchedAt timestamp
        latest_entity = max(
            all_items, key=lambda e: e.get("fetchedAt", "")
        )
        return jsonify(latest_entity)
    except Exception as e:
        logger.exception(f"Failed to retrieve latest cat fact: {e}")
        return jsonify({"error": "Internal server error"}), 500

# GET endpoint with path parameter: get cat fact by ID
@app.route("/catfact/<string:catFactId>", methods=["GET"])
async def get_catfact(catFactId: str):
    """
    GET endpoint to retrieve stored cat fact by ID.
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
            technical_id=catFactId,
        )
        if not entity:
            return (
                jsonify({"error": "CatFact not found", "catFactId": catFactId}),
                404,
            )
        return jsonify(entity)
    except Exception as e:
        logger.exception(f"Failed to retrieve cat fact {catFactId}: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Optional job status GET endpoint (not in original spec, no validation needed)
@app.route("/catfact/job/<string:jobId>", methods=["GET"])
async def get_job_status(jobId: str):
    """
    GET endpoint to check status of a fetch job.
    """
    job = entity_job.get(jobId)
    if not job:
        return jsonify({"error": "Job not found", "jobId": jobId}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(
        use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True
    )