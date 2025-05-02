from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
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
    return current_state  # no transition, remain in current state

async def process_entity(entity_id: str, event: str, params: dict):
    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
        if not entity:
            logger.info(f"Entity {entity_id} not found at processing start.")
            return

        workflow_def = workflows.get(entity_id, default_workflow)

        async with httpx.AsyncClient() as client:
            # TODO: Replace with real Trino query integration when available
            trino_response = await client.get(TRINO_MOCK_API)
            trino_data = trino_response.json()

        current_state = entity.get("currentState", "Created")
        next_state = get_next_state(current_state, event, workflow_def)

        message = ""
        if next_state == "HelloSent":
            lang = params.get("language", "en").lower()
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

        entity["currentState"] = next_state
        entity.setdefault("history", []).append(
            {"state": next_state, "timestamp": datetime.utcnow().isoformat()}
        )
        entity["message"] = message

        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            meta={},
        )

        logger.info(f"Processed entity {entity_id}: event={event}, new_state={next_state}")

    except Exception as e:
        logger.exception(e)


@dataclass
class WorkflowStartRequest:
    entityId: str
    event: str
    parameters: Optional[Dict[str, str]] = None


@dataclass
class WorkflowUpdateRequest:
    entityId: str
    workflowDefinition: Dict[str, Any]


# POST endpoints: validation decorator must go after route decorator (issue workaround)
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
        # create new entity with initial state
        new_entity = {
            "entityId": entity_id,
            "currentState": "Created",
            "history": [{"state": "Created", "timestamp": datetime.utcnow().isoformat()}],
            "message": "",
        }
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=new_entity,
        )
        entity = new_entity

    asyncio.create_task(process_entity(entity_id, event, parameters))

    return jsonify(
        {
            "entityId": entity_id,
            "currentState": entity.get("currentState", ""),
            "message": "Processing started, state may update shortly.",
        }
    )


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


# GET endpoint: validation decorator must go before route decorator (issue workaround)
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