import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

from dataclasses import dataclass, field

@dataclass
class CreateEntityRequest:
    entity_type: str
    initial_data: Optional[Dict[str, Any]] = field(default_factory=dict)
    workflow: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TriggerEventRequest:
    event_name: str
    event_data: Optional[Dict[str, Any]] = field(default_factory=dict)

entity_histories = {}

EXTERNAL_API_URL = "https://api.agify.io"  # Mock external data source

def create_entity_id() -> str:
    return str(uuid.uuid4())

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

async def query_external_data(event_data: dict) -> dict:
    name = event_data.get("name")
    if not name:
        return {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(EXTERNAL_API_URL, params={"name": name}, timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning(f"External API request failed or timed out: {e}")
            return {}

async def process_entity(entity: dict) -> dict:
    # Add created_at timestamp on creation
    entity_data = entity.get("data", {})
    entity_data["created_at"] = now_iso()
    entity["data"] = entity_data
    # Initialize workflow_status and current_state if missing
    if "workflow_status" not in entity:
        entity["workflow_status"] = "created"
    if "current_state" not in entity and "workflow" in entity:
        states = entity["workflow"].get("states", [])
        if states:
            entity["current_state"] = states[0]
    return entity

async def process_entity_event(entity: dict) -> dict:
    # Extract event info injected by endpoint
    event_info = entity.pop("_event_info", None)
    if not event_info:
        # No event info, no processing needed
        return entity

    event_name = event_info.get("event_name")
    event_data = event_info.get("event_data", {})

    current_state = entity.get("current_state")
    workflow = entity.get("workflow", {})
    transitions = workflow.get("transitions", [])

    # Determine valid transition
    transition = next(
        (t for t in transitions if t.get("from") == current_state and t.get("event") == event_name),
        None,
    )

    if not transition:
        logger.info(f"No valid transition for event '{event_name}' from state '{current_state}'")
        new_state = current_state
    else:
        new_state = transition.get("to")

    # Query external data asynchronously and safely
    results = await query_external_data(event_data)

    # Update entity data and state
    updated_data = entity.get("data", {})
    updated_data.update(event_data)
    updated_data.update(results)
    entity["data"] = updated_data
    entity["current_state"] = new_state
    entity["workflow_status"] = "updated"

    # Maintain local history
    entity_id = entity.get("technical_id") or entity.get("id")
    if entity_id:
        history_entry = {
            "timestamp": now_iso(),
            "event": event_name,
            "from_state": current_state,
            "to_state": new_state,
            "metadata": {"event_data": event_data, "external_results": results},
        }
        entity_histories.setdefault(entity_id, []).append(history_entry)

    # Add supplementary entity asynchronously (fire and forget)
    raw_event_entity = {
        "event_name": event_name,
        "event_data": event_data,
        "entity_id": entity_id,
        "timestamp": now_iso(),
    }
    # Protect fire-and-forget from unhandled exceptions
    async def add_raw_event():
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="entity_event_log",
                entity_version=ENTITY_VERSION,
                entity=raw_event_entity,
            )
        except Exception as e:
            logger.warning(f"Failed to add supplementary entity event log: {e}")

    asyncio.create_task(add_raw_event())

    return entity

@app.route("/entities", methods=["POST"])
@validate_request(CreateEntityRequest)
async def create_entity(data: CreateEntityRequest):
    try:
        entity_type = data.entity_type
        initial_data = data.initial_data or {}
        workflow = data.workflow

        if not entity_type or not workflow:
            return jsonify({"error": "Missing required fields: entity_type or workflow"}), 400

        entity_dict = {
            "entity_type": entity_type,
            "workflow": workflow,
            "workflow_status": "created",
            "data": initial_data.copy(),
        }

        # Set current_state to first state if available
        states = workflow.get("states", [])
        if states:
            entity_dict["current_state"] = states[0]

        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_dict,
            workflow=process_entity,
        )

        entity_histories[entity_id] = []

        return jsonify({"entity_id": entity_id, "status": "created"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/entities/<entity_id>/events", methods=["POST"])
@validate_request(TriggerEventRequest)
async def trigger_event(data: TriggerEventRequest, entity_id):
    try:
        event_name = data.event_name
        event_data = data.event_data or {}

        if not event_name:
            return jsonify({"error": "Missing required field: event_name"}), 400

        # Fetch current entity
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
        if not entity:
            return jsonify({"error": "Entity not found"}), 404

        # Inject event info for workflow processing
        entity["_event_info"] = {"event_name": event_name, "event_data": event_data}

        # Update entity with workflow that processes the event
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
            entity=entity,
            workflow=process_entity_event,
        )

        return jsonify(
            {
                "entity_id": entity_id,
                "workflow_status": "processing",
                "message": "Event processed asynchronously via workflow",
            }
        ), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/entities/<entity_id>", methods=["GET"])
async def get_entity(entity_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
        if not entity:
            return jsonify({"error": "Entity not found"}), 404

        return jsonify(
            {
                "entity_id": entity_id,
                "entity_type": entity.get("entity_type"),
                "current_state": entity.get("current_state"),
                "workflow_status": entity.get("workflow_status"),
                "data": entity.get("data"),
            }
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/entities/<entity_id>/history", methods=["GET"])
async def get_entity_history(entity_id):
    try:
        history = entity_histories.get(entity_id)
        if history is None:
            return jsonify({"error": "Entity not found"}), 404

        return jsonify({"entity_id": entity_id, "history": history})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)