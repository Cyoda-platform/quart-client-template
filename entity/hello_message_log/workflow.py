from dataclasses import dataclass
import logging
from datetime import datetime

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloRequest:
    name: str = None  # optional string, primitive type

EXTERNAL_API_URL = "https://httpbin.org/get"

_last_greeting = {"message": "Hello, World!"}

async def process_fetch_external_data(entity: dict):
    """
    Fetch external data and store result in entity['external_message'].
    """
    name = entity.get("name")
    if not name:
        entity['external_message'] = None
        return
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            origin_ip = data.get("origin", "unknown origin")
            entity['external_message'] = f"Hello, {name}! Your origin IP is {origin_ip}."
        except Exception as e:
            logger.exception("Failed to fetch external data")
            entity['external_message'] = f"Hello, {name}!"

async def process_generate_message(entity: dict):
    """
    Generate the greeting message based on external_message or default.
    """
    if entity.get('external_message'):
        entity['message'] = entity['external_message']
    else:
        entity['message'] = "Hello, World!"

async def process_log(entity: dict):
    """
    Log the generated message.
    """
    message = entity.get('message', '')
    logger.info(f"Greeting processed: {message}")

async def process_finalize(entity: dict):
    """
    Finalize entity state.
    """
    entity['status'] = "completed"
    entity['completedAt'] = datetime.utcnow().isoformat()

async def process_fail(entity: dict, exc: Exception):
    """
    Handle failure state.
    """
    entity['status'] = "failed"
    logger.exception(exc)

async def process_hello_message(entity: dict):
    """
    Workflow orchestration function: calls other process_ functions in order.
    Contains no business logic, only orchestration.
    """
    try:
        entity['status'] = "processing"
        entity['requestedAt'] = datetime.utcnow().isoformat()
        await process_fetch_external_data(entity)
        await process_generate_message(entity)
        await process_log(entity)
        await process_finalize(entity)
    except Exception as e:
        await process_fail(entity, e)

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)  # validation last in POST method (workaround for quart-schema issue)
async def post_hello(data: HelloRequest):
    job_entity = {"name": data.name}
    # Fire and forget the processing task. The entity state is kept in job_entity and modified by process_hello_message.
    asyncio.create_task(process_hello_message(job_entity))
    return jsonify({"jobId": datetime.utcnow().isoformat(), "status": "processing"})

@app.route("/hello", methods=["GET"])
async def get_hello():
    return jsonify(_last_greeting)


if __name__ == '__main__':
    import sys
    import asyncio
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)