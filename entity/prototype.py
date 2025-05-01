```python
import asyncio
import logging
from datetime import datetime
from typing import Dict
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence for entities (entityId -> entity data)
entity_store: Dict[str, Dict] = {}

# Possible workflow states
STATE_INITIALIZED = "initialized"
STATE_TRIGGERED = "triggered"
STATE_COMPLETED = "completed"


async def process_entity(entity_id: str, custom_message: str):
    """
    Simulate entity workflow processing triggered by event.
    This function transitions entity from TRIGGERED to COMPLETED,
    and sets the message, potentially enriched by an external API call.
    """
    try:
        logger.info(f"Processing entity {entity_id} with message '{custom_message}'")

        # Update state to triggered
        entity_store[entity_id]["workflowState"] = STATE_TRIGGERED

        # Example of calling a real external API:
        # We'll use a public API that returns a quote, to simulate enrichment of the message.
        # Using: https://api.quotable.io/random
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.quotable.io/random")
            response.raise_for_status()
            quote_data = response.json()
            quote = quote_data.get("content", "")

        # Compose final message combining Hello World (or custom) + quote from API
        final_message = f"{custom_message} — Quote: \"{quote}\""

        # Update entity in store
        entity_store[entity_id].update(
            {
                "workflowState": STATE_COMPLETED,
                "message": final_message,
                "completedAt": datetime.utcnow().isoformat() + "Z",
            }
        )
        logger.info(f"Entity {entity_id} processing completed")
    except Exception as e:
        entity_store[entity_id]["workflowState"] = "error"
        entity_store[entity_id]["message"] = "Processing failed"
        logger.exception(f"Error processing entity {entity_id}: {e}")


@app.route("/api/hello-world/trigger", methods=["POST"])
async def trigger_hello_world():
    """
    POST endpoint to trigger the Hello World workflow.
    Expects JSON body with optional fields:
      - triggerSource: string (optional)
      - customMessage: string (optional, default "Hello World")
    Returns entityId, workflowState, and initial message.
    """
    data = await request.get_json(force=True)
    trigger_source = data.get("triggerSource", "api_call")
    custom_message = data.get("customMessage", "Hello World")

    entity_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    # Initialize entity with state
    entity_store[entity_id] = {
        "entityId": entity_id,
        "workflowState": STATE_INITIALIZED,
        "message": "",
        "triggerSource": trigger_source,
        "requestedAt": requested_at,
    }

    # Fire and forget the workflow processing
    asyncio.create_task(process_entity(entity_id, custom_message))

    # Return initial entity info (processing is async)
    return jsonify(
        {
            "entityId": entity_id,
            "workflowState": entity_store[entity_id]["workflowState"],
            "message": "Processing started",
        }
    ), 202


@app.route("/api/hello-world/<string:entity_id>", methods=["GET"])
async def get_hello_world(entity_id: str):
    """
    GET endpoint to retrieve current state and message of the Hello World entity.
    """
    entity = entity_store.get(entity_id)
    if not entity:
        return jsonify({"error": "Entity not found"}), 404

    return jsonify(
        {
            "entityId": entity["entityId"],
            "workflowState": entity["workflowState"],
            "message": entity.get("message", ""),
        }
    )


if __name__ == "__main__":
    import sys

    # Configure basic logging to console
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
