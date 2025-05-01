from dataclasses import dataclass
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
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
    Calls an external API to get a greeting or related data.
    Here it returns a random quote as a placeholder.
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://api.quotable.io/random", timeout=5.0)
            r.raise_for_status()
            data = r.json()
            quote = data.get("content", "")
            return f"Hello, {name}! Here's a quote for you: \"{quote}\""
        except Exception as e:
            logger.exception(f"Failed to fetch external greeting: {e}")
            # Fallback greeting if external call fails
            return f"Hello, {name}!"

async def process_hello(entity: dict) -> dict:
    """
    Workflow function applied to the 'hello' entity before persistence.
    Enriches the entity by fetching external greetings asynchronously,
    sets the greeting and status directly on the entity dict.
    """
    try:
        name = entity.get("name") or "World"
        entity["status"] = "processing"
        # Ensure requestedAt is ISO8601 string
        if "requestedAt" in entity:
            if isinstance(entity["requestedAt"], datetime):
                entity["requestedAt"] = entity["requestedAt"].isoformat()
        else:
            entity["requestedAt"] = datetime.utcnow().isoformat()

        greeting = await fetch_external_greeting(name)
        entity["greeting"] = greeting
        entity["status"] = "completed"
    except Exception as e:
        logger.exception(f"Exception in process_hello workflow: {e}")
        entity["status"] = "failed"
        entity["greeting"] = None
    return entity

@app.route("/hello", methods=["POST"])
@validate_request(HelloRequest)
async def create_greeting(data: HelloRequest):
    requested_at = datetime.utcnow()

    initial_data = {
        "status": "processing",   # Initial state; will be updated by workflow
        "requestedAt": requested_at.isoformat(),
        "greeting": None,
        "name": data.name or "World"
    }

    try:
        id_created = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=initial_data,
            workflow=process_hello
        )
        return jsonify({"messageId": id_created})
    except Exception as e:
        logger.exception(f"Failed to create greeting: {e}")
        return jsonify({"error": "Failed to create greeting"}), 500

@app.route("/hello/<message_id>", methods=["GET"])
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

        greeting = record.get("greeting")
        if not greeting:
            # Defensive: if greeting missing for completed status, indicate error
            return jsonify({"error": "Greeting data missing"}), 500

        return jsonify({
            "messageId": message_id,
            "greeting": greeting
        })
    except Exception as e:
        logger.exception(f"Failed to retrieve greeting: {e}")
        return jsonify({"error": "Failed to retrieve greeting"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)