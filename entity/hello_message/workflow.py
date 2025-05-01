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

async def process_add_log_entity(entity: dict):
    """
    Add supplementary hello_message_log entity asynchronously.
    """
    name = entity.get("name") or ""
    message = entity.get("message") or ""
    created_at = entity.get("createdAt") or datetime.utcnow().isoformat()
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello_message_log",
            entity_version=ENTITY_VERSION,
            entity={"name": name, "message": message, "loggedAt": created_at},
            workflow=None  # no workflow needed for log entity
        )
    except Exception:
        logger.exception("Failed to add supplementary hello_message_log entity")

async def process_finalize(entity: dict):
    """
    Finalize entity state with timestamp.
    """
    entity['createdAt'] = datetime.utcnow().isoformat()

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