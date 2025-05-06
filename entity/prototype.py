```python
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache for last result (mock persistence)
last_result: Optional[dict] = None

# External APIs
CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"


async def fetch_cat_fact(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_FACT_API)
        resp.raise_for_status()
        data = resp.json()
        return data.get("fact", "No fact found.")
    except Exception as e:
        logger.exception("Failed to fetch cat fact")
        return "Failed to retrieve cat fact."


async def fetch_cat_image_url(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_IMAGE_API)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("url", "No image URL found.")
        return "No image URL found."
    except Exception as e:
        logger.exception("Failed to fetch cat image")
        return "Failed to retrieve cat image."


async def process_entity(entity_job: dict, data: dict):
    """
    Simulate processing job: call external API, compose result, update entity_job.
    """
    async with httpx.AsyncClient() as client:
        cat_type = data.get("type", "fact")
        result = {"message": "Hello World", "catData": None}

        if cat_type == "image":
            cat_data = await fetch_cat_image_url(client)
        else:
            cat_data = await fetch_cat_fact(client)

        result["catData"] = cat_data

        entity_job.update({
            "status": "done",
            "result": result,
            "completedAt": datetime.utcnow().isoformat() + "Z"
        })

        # Update global last_result cache
        global last_result
        last_result = result
        logger.info(f"Processing finished, result stored: {result}")


@app.route("/api/cat/hello", methods=["POST"])
async def cat_hello_post():
    """
    POST endpoint to trigger external data retrieval and compose "Hello World" + cat data.
    Business logic happens here.
    """
    try:
        data = await request.get_json(force=True, silent=True) or {}
        cat_type = data.get("type", "fact")
        if cat_type not in ["fact", "image"]:
            return jsonify({"error": "Invalid type value, must be 'fact' or 'image'"}), 400

        entity_job = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z"
        }

        # Fire and forget processing task
        asyncio.create_task(process_entity(entity_job, data))

        # Return immediate response indicating processing started
        return jsonify({
            "status": "processing",
            "message": "Request accepted and processing started"
        }), 202
    except Exception as e:
        logger.exception("Exception in POST /api/cat/hello")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/cat/hello/latest", methods=["GET"])
async def cat_hello_get_latest():
    """
    GET endpoint to return last stored "Hello World" + cat data result.
    No external calls here, just cached response.
    """
    if last_result is None:
        return jsonify({
            "message": "No data available yet, please POST /api/cat/hello first"
        }), 404
    return jsonify(last_result)


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
