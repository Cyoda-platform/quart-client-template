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

# In-memory data stores (mock persistence)
entities = {}
entity_histories = {}

# Example external API (Trino or similar) - here we use a public API for demo
EXTERNAL_API_URL = "https://api.agify.io"  # Predicts age from name as a placeholder for external data

# Utility functions


def create_entity_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


async def query_external_data(event_data: dict) -> dict:
    """
    Query external API with event_data.
    This example uses agify.io to mock Trino queries via HTTP.
    TODO: Replace with real Trino integration or relevant data source.
    """
    name = event_data.get("name")
    if not name:
        return {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(EXTERNAL_API_URL, params={"name": name})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"External API request failed: {e}")
            return {}


async def process_entity_event(entity_id: str, event_name: str, event_data: dict):
    """
    Process event for entity, update state machine and workflow.
    Mock logic: advance state if transition exists.
    """
    entity = entities.get(entity_id)
    if not entity:
        logger.warning(f"Entity {entity_id} not found during event processing")
        return

    workflow = entity["workflow"]
    current_state = entity["current_state"]
    transitions = workflow.get("transitions", [])

    # Find valid transition
    transition = next(
        (
            t
            for t in transitions
            if t["from"] == current_state and t["event"] == event_name
        ),
        None,
    )

    if not transition:
        logger.info(f"No transition found for event '{event_name}' from state '{current_state}'")
        # No state change, but we still keep history
        new_state = current_state
    else:
        new_state = transition["to"]

    # Query external data if needed
    results = await query_external_data(event_data)

    # Update entity state and data
    entity["current_state"] = new_state
    # Merge event_data and results into entity data
    entity["data"].update(event_data)
    entity["data"].update(results)

    # Update workflow status
    entity["workflow_status"] = "updated"

    # Append history entry
    history_entry = {
        "timestamp": now_iso(),
        "event": event_name,
        "from_state": current_state,
        "to_state": new_state,
        "metadata": {"event_data": event_data, "external_results": results},
    }
    entity_histories.setdefault(entity_id, []).append(history_entry)


@app.route("/entities", methods=["POST"])
async def create_entity():
    try:
        data = await request.get_json(force=True)
        entity_type = data.get("entity_type")
        initial_data = data.get("initial_data", {})
        workflow = data.get("workflow")

        if not entity_type or not workflow:
            return jsonify({"error": "Missing required fields: entity_type or workflow"}), 400

        entity_id = create_entity_id()

        # Initialize entity
        entities[entity_id] = {
            "entity_type": entity_type,
            "current_state": workflow.get("states", [None])[0],
            "workflow": workflow,
            "workflow_status": "created",
            "data": initial_data.copy(),
        }
        entity_histories[entity_id] = []

        return jsonify({"entity_id": entity_id, "status": "created"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/entities/<entity_id>/events", methods=["POST"])
async def trigger_event(entity_id):
    try:
        data = await request.get_json(force=True)
        event_name = data.get("event_name")
        event_data = data.get("event_data", {})

        if not event_name:
            return jsonify({"error": "Missing required field: event_name"}), 400

        if entity_id not in entities:
            return jsonify({"error": "Entity not found"}), 404

        # Fire and forget processing task
        asyncio.create_task(process_entity_event(entity_id, event_name, event_data))

        # Respond immediately while processing occurs asynchronously
        return jsonify(
            {
                "entity_id": entity_id,
                "workflow_status": "processing",
                "message": "Event processing started",
            }
        ), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/entities/<entity_id>", methods=["GET"])
async def get_entity(entity_id):
    try:
        entity = entities.get(entity_id)
        if not entity:
            return jsonify({"error": "Entity not found"}), 404

        return jsonify(
            {
                "entity_id": entity_id,
                "entity_type": entity["entity_type"],
                "current_state": entity["current_state"],
                "workflow_status": entity["workflow_status"],
                "data": entity["data"],
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
```
