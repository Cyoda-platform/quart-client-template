from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloRequest:
    name: str = None  # Optional: name to personalize greeting

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def fetch_external_greeting(name: str) -> str:
    """
    Example of calling a real external API to get a greeting or related data.
    Here we will use an open public API that returns a random quote as a placeholder
    for external data retrieval to demonstrate the pattern.

    TODO: Replace this with a real greeting or name-related external API if needed.
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://api.quotable.io/random")
            r.raise_for_status()
            data = r.json()
            quote = data.get("content", "")
            return f"Hello, {name}! Here's a quote for you: \"{quote}\""
        except Exception as e:
            logger.exception(e)
            # Fallback greeting if external call fails
            return f"Hello, {name}!"

async def process_entity(technical_id: str, data: dict):
    """
    Simulates processing triggered by POST /hello.
    Generates a greeting message, possibly calling external APIs,
    then updates the entity_service with the result.
    """
    try:
        name = data.get("name") or "World"
        greeting = await fetch_external_greeting(name)
        update_data = {
            "greeting": greeting,
            "status": "completed",
            "requestedAt": data.get("requestedAt").isoformat() if data.get("requestedAt") else None,
            "name": name
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=technical_id,
            meta={}
        )
        logger.info(f"Greeting generated and updated for messageId={technical_id}")
    except Exception as e:
        logger.exception(e)
        fail_data = {
            "status": "failed"
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="hello",
                entity_version=ENTITY_VERSION,
                entity=fail_data,
                technical_id=technical_id,
                meta={}
            )
        except Exception as ex:
            logger.exception(ex)

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)  # validation last for POST (workaround issue)
async def create_greeting(data: HelloRequest):
    message_id = str(uuid.uuid4())
    requested_at = datetime.utcnow()

    initial_data = {
        "status": "processing",
        "requestedAt": requested_at.isoformat(),
        "greeting": None,
        "name": data.name or "World"
    }

    try:
        # Add initial item, get technical_id (message_id)
        id_created = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=initial_data
        )
        # Fire and forget processing task
        asyncio.create_task(process_entity(id_created, {"name": data.name, "messageId": id_created, "requestedAt": requested_at}))
        return jsonify({"messageId": id_created})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create greeting"}), 500

@app.route("/hello/<message_id>", methods=["GET"])
# validation first for GET (workaround issue), no body validation needed here
async def get_greeting(message_id):
    try:
        record = await entity_service.get_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            technical_id=message_id
        )
        if not record:
            return jsonify({"error": "messageId not found"}), 404

        status = record.get("status")
        if status != "completed":
            return jsonify({"messageId": message_id, "status": status}), 202

        return jsonify({
            "messageId": message_id,
            "greeting": record.get("greeting")
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve greeting"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)