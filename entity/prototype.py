from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloRequest:
    name: str = None  # optional string, primitive type

# Simple in-memory cache to store last greeting message
_last_greeting = {"message": "Hello, World!"}

# Simulated external API for demonstration: httpbin.org/get to simulate external call
EXTERNAL_API_URL = "https://httpbin.org/get"

async def fetch_external_data(name: str) -> str:
    """
    Simulate external API call that could e.g. personalize or enrich the greeting.
    Here we call httpbin.org/get and use the origin IP as dummy data.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            origin_ip = data.get("origin", "unknown origin")
            return f"Hello, {name}! Your origin IP is {origin_ip}."
        except Exception as e:
            logger.exception("Failed to fetch external data")
            # Fallback greeting if external API fails
            return f"Hello, {name}!"

async def process_hello_message(entity_job: dict, data: dict):
    """
    Background task to process greeting message asynchronously.
    """
    try:
        name = data.get("name")
        if name:
            message = await fetch_external_data(name)
        else:
            message = "Hello, World!"
        # Simulate some processing delay
        await asyncio.sleep(0.5)
        # Update in-memory cache with the new message and timestamp
        entity_job["status"] = "completed"
        entity_job["completedAt"] = datetime.utcnow().isoformat()
        _last_greeting.update({"message": message})
        logger.info(f"Greeting processed: {message}")
    except Exception as e:
        entity_job["status"] = "failed"
        logger.exception(e)

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)  # validation last in POST method (workaround for quart-schema issue)
async def post_hello(data: HelloRequest):
    """
    POST /hello
    Accepts optional JSON body with "name" field.
    Triggers background processing of greeting message.
    Returns immediate status with job id.
    """
    job_id = datetime.utcnow().isoformat()
    entity_job = {"status": "processing", "requestedAt": job_id}
    # Fire and forget background processing
    asyncio.create_task(process_hello_message(entity_job, data.__dict__))
    # Return job status and id immediately
    return jsonify({"jobId": job_id, "status": entity_job["status"]})

@app.route("/hello", methods=["GET"])
# validation first in GET method (workaround for quart-schema issue)
async def get_hello():
    """
    GET /hello
    Returns the last generated greeting message.
    No validation needed since no query params to validate.
    """
    return jsonify(_last_greeting)


if __name__ == '__main__':
    import sys
    import httpx
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
