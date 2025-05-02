from dataclasses import dataclass
from typing import Dict, Any, Optional

import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

workflows: Dict[str, Dict[str, Any]] = {}

default_workflow = {
    "states": ["Created", "HelloSent", "Completed"],
    "transitions": [
        {"from": "Created", "to": "HelloSent", "event": "StartGreeting"},
        {"from": "HelloSent", "to": "Completed", "event": "Complete"},
    ],
}

TRINO_MOCK_API = "https://httpbin.org/delay/1"  # simulates 1 second delay


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)


def get_next_state(current_state: str, event: str, workflow_def: dict) -> str:
    for t in workflow_def.get("transitions", []):
        if t["from"] == current_state and t["event"] == event:
            return t["to"]
    return current_state  # no transition found, remain in current state


# Workflow function for entity model 'entity'
async def process_entity(entity: dict) -> dict:
    """
    Workflow function applied to the 'entity' before persistence.
    Handles state transitions, external async calls, and message updates.
    """
    entity_id = entity.get("entityId")
    if not entity_id:
        logger.warning("Entity missing 'entityId' in workflow function.")
        return entity

    workflow_def = workflows.get(entity_id, default_workflow)

    # Read event and parameters injected into the entity
    event = entity.get("_pendingEvent")
    parameters = entity.get("_pendingParameters", {})

    # If no event, just return entity without changes
    if not event:
        return entity

    current_state = entity.get("currentState", "Created")

    # Simulate external API call before state transition (e.g., Trino query)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            trino_response = await client.get(TRINO_MOCK_API)
            trino_response.raise_for_status()
            trino_data = trino_response.json()
            # Optional: store/use trino_data if needed
    except Exception as e:
        logger.warning(f"Failed to fetch Trino mock data for entity {entity_id}: {e}")

    # Determine the next state based on current state and event
    next_state = get_next_state(current_state, event, workflow_def)

    # Construct message based on next state
    message = ""
    if next_state == "HelloSent":
        lang = str(parameters.get("language", "en")).lower()
        greetings = {
            "en": "Hello World",
            "es": "Hola Mundo",
            "fr": "Bonjour le monde",
            "de": "Hallo Welt",
            "it": "Ciao Mondo",
        }
        message = greetings.get(lang, greetings["en"])
    elif next_state == current_state:
        message = f"No transition found for event '{event}' from state '{current_state}'."
    else:
        message = f"Transitioned to state '{next_state}'."

    # Update entity state and append to history
    entity["currentState"] = next_state
    entity.setdefault("history", [])
    # Avoid duplicate consecutive states in history
    if not entity["history"] or entity["history"][-1].get("state") != next_state:
        entity["history"].append(
            {"state": next_state, "timestamp": datetime.utcnow().isoformat()}
        )
    entity["message"] = message

    # Clean up temporary event/parameter fields so they're not persisted
    entity.pop("_pendingEvent", None)
    entity.pop("_pendingParameters", None)

    return entity


@dataclass
class WorkflowStartRequest:
    entityId: str
    event: str
    parameters: Optional[Dict[str, str]] = None


@dataclass
class WorkflowUpdateRequest:
    entityId: str
    workflowDefinition: Dict[str, Any]


# POST endpoint to start or continue a workflow
@app.route("/workflow/start", methods=["POST"])
@validate_request(WorkflowStartRequest)
async def start_workflow(data: WorkflowStartRequest):
    entity_id = data.entityId
    event = data.event
    parameters = data.parameters or {}

    entity = await entity_service.get_item(
        token=cyoda_token,
        entity_model="entity",
        entity_version=ENTITY_VERSION,
        technical_id=entity_id,
    )

    if not entity:
        # Create new entity with initial state and pending event/parameters
        new_entity = {
            "entityId": entity_id,
            "currentState": "Created",
            "history": [{"state": "Created", "timestamp": datetime.utcnow().isoformat()}],
            "message": "",
            # Inject event and parameters for workflow function
            "_pendingEvent": event,
            "_pendingParameters": parameters,
        }
        # Add item with workflow function to process entity before persisting
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=new_entity,
            workflow=process_entity,
        )
        entity = new_entity

    else:
        # For existing entity, inject event and parameters, then update entity with workflow function
        entity["_pendingEvent"] = event
        entity["_pendingParameters"] = parameters

        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            workflow=process_entity,
            meta={},
        )

    return jsonify(
        {
            "entityId": entity_id,
            "currentState": entity.get("currentState", ""),
            "message": "Processing started, state may update shortly.",
        }
    )


# POST endpoint to update workflow definition for an entity
@app.route("/workflow/update", methods=["POST"])
@validate_request(WorkflowUpdateRequest)
async def update_workflow(data: WorkflowUpdateRequest):
    entity_id = data.entityId
    workflow_def = data.workflowDefinition

    if not isinstance(workflow_def.get("states"), list) or not isinstance(workflow_def.get("transitions"), list):
        return jsonify({"error": "Invalid workflowDefinition format"}), 400

    workflows[entity_id] = workflow_def

    logger.info(f"Workflow updated for entity {entity_id}")
    return jsonify({"entityId": entity_id, "status": "Workflow updated successfully"})


# GET endpoint to get current state and history of an entity
@app.route("/entity/<string:entity_id>/state", methods=["GET"])
async def get_entity_state(entity_id):
    entity = await entity_service.get_item(
        token=cyoda_token,
        entity_model="entity",
        entity_version=ENTITY_VERSION,
        technical_id=entity_id,
    )
    if not entity:
        return jsonify({"error": "Entity not found"}), 404

    return jsonify(
        {
            "entityId": entity_id,
            "currentState": entity.get("currentState", ""),
            "history": entity.get("history", []),
            "message": entity.get("message", ""),
        }
    )


if __name__ == '__main__':
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)