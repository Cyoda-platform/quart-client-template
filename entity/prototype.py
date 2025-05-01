```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence: messageId -> {"greeting": str, "createdAt": datetime}
entity_job = {}


async def fetch_external_greeting(name: str) -> str:
    """
    Example of calling a real external API to get a greeting or related data.
    Here we will use an open public API that returns a random quote as a placeholder
    for external data retrieval to demonstrate the pattern.

    TODO: Replace this with a real greeting or name-related external API if needed.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Using a public API to get a random quote as a placeholder external call
            r = await client.get("https://api.quotable.io/random")
            r.raise_for_status()
            data = r.json()
            quote = data.get("content", "")
            return f"Hello, {name}! Here's a quote for you: \"{quote}\""
        except Exception as e:
            logger.exception(e)
            # Fallback greeting if external call fails
            return f"Hello, {name}!"


async def process_entity(entity_cache: dict, data: dict):
    """
    Simulates processing triggered by POST /hello.
    Generates a greeting message, possibly calling external APIs.
    """
    try:
        name = data.get("name") or "World"
        greeting = await fetch_external_greeting(name)
        message_id = data.get("messageId")
        entity_cache[message_id]["greeting"] = greeting
        entity_cache[message_id]["status"] = "completed"
        logger.info(f"Greeting generated for messageId={message_id}")
    except Exception as e:
        logger.exception(e)
        message_id = data.get("messageId")
        entity_cache[message_id]["status"] = "failed"


@app.route("/hello", methods=["POST"])
async def create_greeting():
    data = await request.get_json()
    if data is None:
        data = {}

    message_id = str(uuid.uuid4())
    requested_at = datetime.utcnow()

    # Store initial job info with status = processing
    entity_job[message_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "greeting": None,
    }

    # Fire and forget processing task
    asyncio.create_task(process_entity(entity_job, {"name": data.get("name"), "messageId": message_id}))

    return jsonify({"messageId": message_id})


@app.route("/hello/<message_id>", methods=["GET"])
async def get_greeting(message_id):
    record = entity_job.get(message_id)
    if not record:
        return jsonify({"error": "messageId not found"}), 404

    if record["status"] != "completed":
        return jsonify({"messageId": message_id, "status": record["status"]}), 202

    return jsonify({
        "messageId": message_id,
        "greeting": record["greeting"]
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
