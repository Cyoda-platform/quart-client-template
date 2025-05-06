from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to store last processed result
last_result_cache: Optional[dict] = None

# External APIs URLs
CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"


@dataclass
class HelloRequest:
    type: str  # expected values: "image", "fact", "greeting"


async def fetch_cat_fact(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_FACT_API)
        resp.raise_for_status()
        data = resp.json()
        return data.get("fact", "No fact available")
    except Exception as e:
        logger.exception(e)
        return "Failed to fetch cat fact"


async def fetch_cat_image_url(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_IMAGE_API)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0].get("url", "")
        return ""
    except Exception as e:
        logger.exception(e)
        return ""


async def process_hello_request(data: HelloRequest) -> dict:
    """
    Process the POST /api/cats/hello request according to `type`.
    Returns dict with keys: message, data (or None)
    """
    global last_result_cache
    async with httpx.AsyncClient() as client:
        cat_type = data.type if data.type else "greeting"
        message = "Hello, Cat Lover!"
        cat_data = None

        if cat_type == "fact":
            cat_data = await fetch_cat_fact(client)
        elif cat_type == "image":
            cat_data = await fetch_cat_image_url(client)
        elif cat_type == "greeting":
            cat_data = None
        else:
            cat_data = None

        result = {
            "message": message,
            "data": cat_data,
        }

        # Store result with timestamp
        last_result_cache = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **result,
        }
        return result


@app.route("/api/cats/hello", methods=["POST"])
@validate_request(HelloRequest)  # Validation last in POST method (issue workaround)
async def cats_hello_post(data: HelloRequest):
    # Fire and forget pattern: process in background
    # But for UX verification, we wait for completion here to return result immediately
    try:
        result = await process_hello_request(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error", "data": None}), 500


@app.route("/api/cats/hello/result", methods=["GET"])
async def cats_hello_get():
    # GET with no request body or query params - no validation needed
    if last_result_cache is None:
        return jsonify(
            {"message": "No results available yet", "data": None, "timestamp": None}
        ), 404
    return jsonify(last_result_cache)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
