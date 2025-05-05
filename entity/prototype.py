from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory storage for CatFact entities
catfact_store: Dict[str, Dict] = {}

# In-memory storage for workflow jobs status
entity_job: Dict[str, Dict] = {}

CAT_FACT_API_URL = "https://catfact.ninja/fact"

@dataclass
class EmptyBody:
    pass

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
    Workflow: fetch cat fact and store it in the in-memory store.
    """
    try:
        entity_job[job_id]["status"] = "fetching"
        fact = await fetch_cat_fact_from_api()
        if not fact:
            entity_job[job_id]["status"] = "failed"
            return

        entity_job[job_id]["status"] = "storing"

        # Create entity with unique ID
        entity_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat() + "Z"
        catfact_store[entity_id] = {
            "catFactId": entity_id,
            "fact": fact,
            "fetchedAt": now_iso,
        }

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

# GET endpoint without parameters: no validation needed
@app.route("/catfact/latest", methods=["GET"])
async def get_latest_catfact():
    """
    GET endpoint to retrieve the most recently fetched cat fact.
    """
    if not catfact_store:
        return jsonify({"error": "No cat facts stored yet"}), 404

    # Find entity with latest fetchedAt timestamp
    latest_entity = max(
        catfact_store.values(), key=lambda e: e["fetchedAt"]
    )
    return jsonify(latest_entity)

# GET endpoint with path parameter: no validation needed
@app.route("/catfact/<string:catFactId>", methods=["GET"])
async def get_catfact(catFactId: str):
    """
    GET endpoint to retrieve stored cat fact by ID.
    """
    entity = catfact_store.get(catFactId)
    if not entity:
        return (
            jsonify({"error": "CatFact not found", "catFactId": catFactId}),
            404,
        )
    return jsonify(entity)

# Optional GET endpoint with query parameters example (not specified, shown as example)
# For illustration only, not part of original spec
# GET requests with query parameters require validation first per quart-schema issue workaround
# from quart_schema import validate_querystring
# @validate_querystring(SomeQueryModel)
# @app.route("/somepath", methods=["GET"])
# async def some_get_endpoint():
#     # standard request.args usage here

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
```