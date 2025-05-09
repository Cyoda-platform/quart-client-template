```python
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema

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


async def fetch_external_api(entity_id: str):
    """
    Async fetch external API, update the entity with results and fetch_status.
    """
    entity = entities.get(entity_id)
    if not entity:
        logger.warning(f"Entity {entity_id} not found for fetch")
        return

    url_node = entity.get("api_url")
    # api_url stored as JSON string, parse it or just treat as string if needed
    # For prototype, assume api_url is string inside the JSON node
    try:
        # If api_url is a JSON string node, parse it to str; else use directly
        # The spec says api_url is JsonNode but user input is JSON string, so here treat as string
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

    # Update entity atomically
    entity.update({
        "fetched_data": fetched_data,
        "fetched_at": fetched_at,
        "fetch_status": fetch_status,
    })


async def process_entity_fetch(entity_id: str):
    """
    Fire-and-forget async task to fetch and update entity data.
    """
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
async def create_entity():
    data = await request.get_json(force=True)
    api_url = data.get("api_url")
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

    # Fire and forget async fetch
    asyncio.create_task(process_entity_fetch(entity_id))

    return jsonify(entity), 201


@app.route("/entities/<entity_id>", methods=["POST"])
async def update_entity(entity_id):
    entity = entities.get(entity_id)
    if not entity:
        abort(404, description="Entity not found")

    data = await request.get_json(force=True)
    api_url = data.get("api_url")
    if api_url is None:
        return jsonify({"error": "api_url field is required"}), 400

    entity["api_url"] = api_url
    # Note: fetched_data and fetched_at keep previous values until fetch runs

    # Fire and forget async fetch
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
    import logging.config

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
