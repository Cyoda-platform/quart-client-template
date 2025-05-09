from dataclasses import dataclass
from typing import Optional, Any
import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" for prototype
entities = {}

# Job tracking dictionary, job_id -> status info
entity_jobs = {}

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class ApiUrlPayload:
    api_url: Any  # JsonNode; type Any to allow JSON string or other JSON types

async def fetch_external_api(entity_id: str):
    entity = entities.get(entity_id)
    if not entity:
        logger.warning(f"Entity {entity_id} not found for fetch")
        return

    url_node = entity.get("api_url")
    try:
        api_url = url_node if isinstance(url_node, str) else str(url_node)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        fetch_status = "success"
        fetched_data = data
        fetched_at = utc_now_iso()
    except Exception as e:
        logger.exception(f"Failed to fetch external API for entity {entity_id}: {e}")
        fetch_status = str(e)
        fetched_data = None
        fetched_at = None

    entity.update({
        "fetched_data": fetched_data,
        "fetched_at": fetched_at,
        "fetch_status": fetch_status,
    })

async def process_entity_fetch(entity_id: str):
    job_id = str(uuid4())
    requested_at = utc_now_iso()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    try:
        await fetch_external_api(entity_id)
        entity_jobs[job_id]["status"] = "done"
    except Exception as e:
        logger.exception(f"Error processing fetch for entity {entity_id}: {e}")
        entity_jobs[job_id]["status"] = f"error: {e}"

@app.route("/entities", methods=["POST"])
@validate_request(ApiUrlPayload)  # validation last for POST (workaround issue)
async def create_entity(data: ApiUrlPayload):
    api_url = data.api_url
    if api_url is None:
        return jsonify({"error": "api_url field is required"}), 400

    entity_id = str(uuid4())
    entity = {
        "id": entity_id,
        "api_url": api_url,
        "fetched_data": None,
        "fetched_at": None,
        "fetch_status": None,
    }
    entities[entity_id] = entity

    asyncio.create_task(process_entity_fetch(entity_id))

    return jsonify(entity), 201

@app.route("/entities/<entity_id>", methods=["POST"])
@validate_request(ApiUrlPayload)  # validation last for POST (workaround issue)
async def update_entity(entity_id, data: ApiUrlPayload):
    entity = entities.get(entity_id)
    if not entity:
        abort(404, description="Entity not found")

    api_url = data.api_url
    if api_url is None:
        return jsonify({"error": "api_url field is required"}), 400

    entity["api_url"] = api_url

    asyncio.create_task(process_entity_fetch(entity_id))

    return jsonify(entity)

@app.route("/entities/<entity_id>/fetch", methods=["POST"])
async def manual_fetch(entity_id):
    entity = entities.get(entity_id)
    if not entity:
        abort(404, description="Entity not found")

    await fetch_external_api(entity_id)
    return jsonify({
        "id": entity["id"],
        "fetched_data": entity["fetched_data"],
        "fetched_at": entity["fetched_at"],
        "fetch_status": entity["fetch_status"],
    })

# No validation needed for GET requests without query params as per instructions
@app.route("/entities", methods=["GET"])
async def get_all_entities():
    return jsonify(list(entities.values()))

@app.route("/entities/<entity_id>", methods=["GET"])
async def get_entity_by_id(entity_id):
    entity = entities.get(entity_id)
    if not entity:
        abort(404, description="Entity not found")
    return jsonify(entity)

@app.route("/entities/<entity_id>", methods=["DELETE"])
async def delete_entity(entity_id):
    if entity_id in entities:
        del entities[entity_id]
        return "", 204
    abort(404, description="Entity not found")

@app.route("/entities", methods=["DELETE"])
async def delete_all_entities():
    entities.clear()
    return "", 204

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```