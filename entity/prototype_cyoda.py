from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Possible workflow states
STATE_INITIALIZED = "initialized"
STATE_TRIGGERED = "triggered"
STATE_COMPLETED = "completed"


@dataclass
class TriggerRequest:
    triggerSource: str = "api_call"
    customMessage: str = "Hello World"


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)


async def process_entity(entity_id: str, custom_message: str):
    """
    Simulate entity workflow processing triggered by event.
    This function transitions entity from TRIGGERED to COMPLETED,
    and sets the message, potentially enriched by an external API call.
    """
    try:
        logger.info(f"Processing entity {entity_id} with message '{custom_message}'")

        # Retrieve current entity data
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="hello_world",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
        if not entity:
            logger.error(f"Entity {entity_id} not found during processing")
            return

        # Update state to triggered
        entity["workflowState"] = STATE_TRIGGERED

        await entity_service.update_item(
            token=cyoda_token,
            entity_model="hello_world",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            meta={},
        )

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

        # Update entity with completed state and message
        entity.update(
            {
                "workflowState": STATE_COMPLETED,
                "message": final_message,
                "completedAt": datetime.utcnow().isoformat() + "Z",
            }
        )
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="hello_world",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            meta={},
        )
        logger.info(f"Entity {entity_id} processing completed")
    except Exception as e:
        logger.exception(f"Error processing entity {entity_id}: {e}")
        try:
            entity = await entity_service.get_item(
                token=cyoda_token,
                entity_model="hello_world",
                entity_version=ENTITY_VERSION,
                technical_id=entity_id,
            )
            if entity:
                entity["workflowState"] = "error"
                entity["message"] = "Processing failed"
                await entity_service.update_item(
                    token=cyoda_token,
                    entity_model="hello_world",
                    entity_version=ENTITY_VERSION,
                    entity=entity,
                    technical_id=entity_id,
                    meta={},
                )
        except Exception as e2:
            logger.exception(f"Error updating entity {entity_id} to error state: {e2}")


@app.route("/api/hello-world/trigger", methods=["POST"])
@validate_request(TriggerRequest)  # validation last for POST per workaround
async def trigger_hello_world(data: TriggerRequest):
    """
    POST endpoint to trigger the Hello World workflow.
    Expects JSON body with optional fields:
      - triggerSource: string (optional)
      - customMessage: string (optional, default "Hello World")
    Returns entityId, workflowState, and initial message.
    """
    trigger_source = data.triggerSource
    custom_message = data.customMessage

    entity_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    # Initialize entity with state
    entity_data = {
        "entityId": entity_id,
        "workflowState": STATE_INITIALIZED,
        "message": "",
        "triggerSource": trigger_source,
        "requestedAt": requested_at,
    }

    # Add entity via entity_service
    try:
        _id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello_world",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
        )
    except Exception as e:
        logger.exception(f"Error adding entity: {e}")
        return jsonify({"error": "Failed to create entity"}), 500

    # Fire and forget the workflow processing
    # Use the generated entity_id, as entity_service returns id but we use the same here
    asyncio.create_task(process_entity(entity_id, custom_message))

    # Return initial entity info (processing is async)
    return jsonify(
        {
            "entityId": entity_id,
            "workflowState": STATE_INITIALIZED,
            "message": "Processing started",
        }
    ), 202


# GET endpoint has no request body, no validation needed per spec
@app.route("/api/hello-world/<string:entity_id>", methods=["GET"])
async def get_hello_world(entity_id: str):
    """
    GET endpoint to retrieve current state and message of the Hello World entity.
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="hello_world",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception as e:
        logger.exception(f"Error retrieving entity {entity_id}: {e}")
        return jsonify({"error": "Failed to retrieve entity"}), 500

    if not entity:
        return jsonify({"error": "Entity not found"}), 404

    return jsonify(
        {
            "entityId": entity.get("entityId", entity_id),
            "workflowState": entity.get("workflowState", ""),
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