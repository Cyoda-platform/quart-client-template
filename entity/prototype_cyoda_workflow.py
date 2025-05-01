from dataclasses import dataclass
import logging
from datetime import datetime

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloRequest:
    name: str = None  # optional string

EXTERNAL_API_URL = "https://httpbin.org/get"

async def fetch_external_data(name: str) -> str:
    """
    Simulate external API call that could e.g. personalize or enrich the greeting.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            origin_ip = data.get("origin", "unknown origin")
            return f"Hello, {name}! Your origin IP is {origin_ip}."
        except Exception:
            logger.exception("Failed to fetch external data")
            return f"Hello, {name}!"

async def process_hello_message(entity: dict) -> dict:
    """
    Workflow function applied to the entity asynchronously before persistence.
    This function enriches the entity with a greeting message and adds a timestamp.
    It can also add supplementary entities of different models.
    """
    name = entity.get("name")
    if name:
        message = await fetch_external_data(name)
    else:
        message = "Hello, World!"

    entity["message"] = message
    entity["createdAt"] = datetime.utcnow().isoformat()

    # Example: add supplementary entity of different model, allowed by rules
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello_message_log",
            entity_version=ENTITY_VERSION,
            entity={"name": name or "", "message": message, "loggedAt": entity["createdAt"]},
            workflow=None  # no workflow needed for log entity
        )
    except Exception:
        logger.exception("Failed to add supplementary hello_message_log entity")

    return entity

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)
async def post_hello(data: HelloRequest):
    """
    POST /hello
    Minimal controller: calls add_item with workflow function to handle async processing.
    Returns the persisted entity ID or error response.
    """
    entity_name = "hello_message"
    try:
        entity = {"name": data.name}
        entity_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_hello_message,
        )
        return jsonify({"entityId": entity_id})
    except Exception:
        logger.exception("Failed to add hello message")
        return jsonify({"error": "Failed to add hello message"}), 500

@app.route("/hello", methods=["GET"])
async def get_hello():
    """
    GET /hello
    Returns the most recent greeting message or default if none available.
    """
    entity_name = "hello_message"
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"message": "Hello, World!"})
        # Return the most recent message by createdAt descending safely
        latest_item = max(items, key=lambda x: x.get("createdAt", ""))
        return jsonify({"message": latest_item.get("message", "Hello, World!")})
    except Exception:
        logger.exception("Failed to retrieve greeting messages")
        return jsonify({"message": "Hello, World!"})

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)