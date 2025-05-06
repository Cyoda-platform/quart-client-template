from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CatFetchRequest:
    type: str  # "image" or "fact"

# In-memory storage for fetched cat data results.
# Structure: {request_id: {"type": str, "data": str, "requestedAt": datetime, "status": str}}
entity_job = {}


async def fetch_cat_image() -> str:
    """
    Fetch a random cat image URL from The Cat API.
    Docs: https://docs.thecatapi.com/
    """
    url = "https://api.thecatapi.com/v1/images/search"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # data is a list of images, take the first image url
            return data[0]["url"]
        except Exception as e:
            logger.exception(f"Error fetching cat image: {e}")
            return ""


async def fetch_cat_fact() -> str:
    """
    Fetch a random cat fact from Cat Facts API.
    Docs: https://catfact.ninja/fact
    """
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("fact", "")
        except Exception as e:
            logger.exception(f"Error fetching cat fact: {e}")
            return ""


async def process_entity(request_id: str, requested_type: str):
    """
    Background processing task to fetch cat data (image or fact)
    and update the in-memory store.
    """
    try:
        if requested_type == "image":
            data = await fetch_cat_image()
        elif requested_type == "fact":
            data = await fetch_cat_fact()
        else:
            logger.warning(f"Unknown type requested: {requested_type}")
            data = ""

        entity_job[request_id]["data"] = data
        entity_job[request_id]["status"] = "completed"
        logger.info(f"Completed processing for request_id={request_id}")

    except Exception as e:
        entity_job[request_id]["status"] = "failed"
        logger.exception(f"Processing failed for request_id={request_id}: {e}")


@app.route("/cats/fetch", methods=["POST"])
@validate_request(CatFetchRequest)  # validation last for POST (issue workaround)
async def cats_fetch(data: CatFetchRequest):
    """
    POST /cats/fetch
    Request JSON: { "type": "image" | "fact" }
    Response JSON: { "requestId": "string" }
    """
    try:
        requested_type = data.type
        if requested_type not in ("image", "fact"):
            return jsonify({"error": "Invalid type. Must be 'image' or 'fact'."}), 400

        request_id = str(uuid.uuid4())
        requested_at = datetime.utcnow()

        # Store initial processing state
        entity_job[request_id] = {
            "type": requested_type,
            "data": None,
            "requestedAt": requested_at.isoformat() + "Z",
            "status": "processing",
        }

        # Fire and forget the processing task
        asyncio.create_task(process_entity(request_id, requested_type))

        return jsonify({"requestId": request_id})

    except Exception as e:
        logger.exception(f"Error in /cats/fetch endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/cats/result/<string:request_id>", methods=["GET"])
# No request body or query validation needed here as per requirements
async def cats_result(request_id: str):
    """
    GET /cats/result/{requestId}
    Response JSON:
    {
      "requestId": "string",
      "type": "image" | "fact",
      "data": "string",
      "status": "processing" | "completed" | "failed",
      "requestedAt": "ISO8601 string"
    }
    """
    try:
        record = entity_job.get(request_id)
        if record is None:
            return jsonify({"error": "requestId not found"}), 404

        return jsonify({
            "requestId": request_id,
            "type": record["type"],
            "data": record["data"],
            "status": record["status"],
            "requestedAt": record["requestedAt"],
        })

    except Exception as e:
        logger.exception(f"Error in /cats/result/{request_id} endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```