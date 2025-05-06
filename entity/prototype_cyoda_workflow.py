from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Optional
import uuid
import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory job status tracking dictionary
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

async def process_CatFact(entity: dict) -> dict:
    """
    Workflow function: asynchronously fetch cat fact and enrich entity before persistence.
    Tracks job status in-memory using '_jobId' in entity.
    """
    job_id = entity.get("_jobId")
    if job_id:
        # Preserve requestedAt if available, else set to now
        requested_at = entity_job.get(job_id, {}).get("requestedAt") or datetime.utcnow().isoformat() + "Z"
        entity_job[job_id] = {"status": "fetching", "requestedAt": requested_at}

    fact = await fetch_cat_fact_from_api()
    if not fact:
        if job_id:
            entity_job[job_id]["status"] = "failed"
        entity["error"] = "Failed to fetch cat fact"
        return entity

    now_iso = datetime.utcnow().isoformat() + "Z"
    entity["fact"] = fact
    entity["fetchedAt"] = now_iso

    if job_id:
        entity_job[job_id]["status"] = "completed"
        # Entity ID will be set by persistence layer, no modification here

    return entity

@app.route("/catfact/fetch", methods=["POST"])
@validate_request(EmptyBody)
async def fetch_catfact(data: EmptyBody):
    """
    POST endpoint to trigger fetching and storing a new cat fact.
    Creates minimal entity with job id to be processed by workflow function.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Minimal entity with _jobId for tracking inside workflow
    initial_entity = {"_jobId": job_id}

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
            workflow=process_CatFact,
        )
    except Exception as e:
        logger.exception(f"Failed to add CatFact entity: {e}")
        entity_job[job_id]["status"] = "failed"
        return jsonify({"status": "error", "message": "Failed to start cat fact fetch job"}), 500

    entity_job[job_id]["catFactId"] = entity_id

    return jsonify({
        "status": "success",
        "message": "Cat fact fetch job started",
        "jobId": job_id,
        "entityId": entity_id,
    }), 202

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

        # Filter out entities missing 'fetchedAt' or with errors
        valid_items = [e for e in all_items if e.get("fetchedAt") and not e.get("error")]
        if not valid_items:
            return jsonify({"error": "No valid cat facts stored yet"}), 404

        latest_entity = max(valid_items, key=lambda e: e.get("fetchedAt", ""))
        return jsonify(latest_entity)
    except Exception as e:
        logger.exception(f"Failed to retrieve latest cat fact: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/catfact/<string:catFactId>", methods=["GET"])
async def get_catfact(catFactId: str):
    """
    GET endpoint to retrieve a stored cat fact by its ID.
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
            technical_id=catFactId,
        )
        if not entity:
            return jsonify({"error": "CatFact not found", "catFactId": catFactId}), 404
        if entity.get("error"):
            # Entity exists but processing failed
            return jsonify({"error": "CatFact processing failed", "catFactId": catFactId}), 500
        return jsonify(entity)
    except Exception as e:
        logger.exception(f"Failed to retrieve cat fact {catFactId}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/catfact/job/<string:jobId>", methods=["GET"])
async def get_job_status(jobId: str):
    """
    GET endpoint to check the status of a cat fact fetch job.
    """
    job = entity_job.get(jobId)
    if not job:
        return jsonify({"error": "Job not found", "jobId": jobId}), 404
    return jsonify(job)

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)