from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Dict
import uuid

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

STATE_INITIALIZED = "initialized"
STATE_TRIGGERED = "triggered"
STATE_COMPLETED = "completed"
STATE_ERROR = "error"


@dataclass
class TriggerRequest:
    triggerSource: str = "api_call"
    customMessage: str = "Hello World"


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)


async def process_hello_world(entity: Dict) -> None:
    """
    Workflow function that performs the entire lifecycle of the entity:
    - sets initial state
    - calls external API
    - transitions states (initialized -> triggered -> completed)
    - modifies entity in place (no add/update/delete for this entity_model)
    """
    try:
        # Step 1: Initialize entity state and attributes
        entity["workflowState"] = STATE_INITIALIZED
        entity["message"] = ""
        if "requestedAt" not in entity:
            entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Entity {entity.get('entityId')} initialized")

        # Step 2: Transition to triggered state
        entity["workflowState"] = STATE_TRIGGERED

        # Step 3: Call external API to enrich the message
        custom_message = entity.get("customMessage", "Hello World")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.quotable.io/random")
            response.raise_for_status()
            quote_data = response.json()
            quote = quote_data.get("content", "")

        final_message = f"{custom_message} — Quote: \"{quote}\""

        # Step 4: Transition to completed state with final message
        entity["workflowState"] = STATE_COMPLETED
        entity["message"] = final_message
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"

        logger.info(f"Entity {entity.get('entityId')} processing completed")

    except Exception as e:
        logger.exception(f"Error in process_hello_world workflow for entity {entity.get('entityId')}: {e}")
        entity["workflowState"] = STATE_ERROR
        entity["message"] = "Processing failed"


@app.route("/api/hello-world/trigger", methods=["POST"])
@validate_request(TriggerRequest)
async def trigger_hello_world(data: TriggerRequest):
    """
    Thin endpoint handler:
    - generate entityId
    - prepare entity dict including request data
    - call entity_service.add_item with workflow function to do all async work before persisting
    - return persisted entity info immediately (workflow already done)
    """
    entity_id = str(uuid.uuid4())

    entity_data = {
        "entityId": entity_id,
        "triggerSource": data.triggerSource,
        "customMessage": data.customMessage,
        # workflowState, message, timestamps will be set inside workflow function
    }

    try:
        # Add entity with workflow: process_hello_world
        # This call will await workflow, so entity_data is fully processed before persistence
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello_world",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_hello_world,
        )
    except Exception as e:
        logger.exception(f"Failed to add entity: {e}")
        return jsonify({"error": "Failed to create entity"}), 500

    # Return the fully processed entity info
    return jsonify(
        {
            "entityId": entity_id,
            "workflowState": entity_data.get("workflowState", ""),
            "message": entity_data.get("message", ""),
        }
    ), 201


@app.route("/api/hello-world/<string:entity_id>", methods=["GET"])
async def get_hello_world(entity_id: str):
    """
    Retrieve persisted entity state and message.
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

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)