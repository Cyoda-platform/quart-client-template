Absolutely, moving all the entity-related asynchronous logic into the workflow functions is the right approach. This will keep the endpoint handlers clean and focused on request/response handling, while the business logic and side effects related to entity state transitions, external data queries, and event processing reside inside the appropriate `process_{entity_name}` workflow functions.

---

### What to do:
- Move the logic from the event processing endpoint (`process_entity_event`) into a workflow function, say `process_entity_event_workflow`.
- Modify the entity in-place inside that workflow function.
- Use `entity_service.add_item()` or `update_item()` for the entity itself **only once** after the workflow modifies the entity.
- For any supplementary entities, you can still call entity_service to add/update them.
- The `process_entity` workflow function used in entity creation should remain and can be extended as needed.
- The event trigger endpoint will now update the entity by calling `update_item` with the workflow function responsible for processing the event.

---

### Proposed changes:

1. **Refactor event processing logic into `process_entity_event_workflow(entity: dict, event_name: str, event_data: dict) -> dict`**
   - This function will be async, accept `entity` as input (the current entity dict).
   - It will modify the entity's current state and data directly.
   - Query external data asynchronously.
   - Add history entries as supplementary entities or store locally.
   - It will return the modified entity dict, which will be persisted by `entity_service.update_item()`.

2. **Update the event trigger endpoint to:**
   - Fetch the entity.
   - Call `entity_service.update_item()` with `workflow=process_entity_event_workflow` and pass event info inside the entity or meta.
   - The workflow function will have access to the event info to process it.

---

### Important notes:

- Since `entity_service.add/update_item` workflows take only the entity dict as argument, but in event processing we need event_name and event_data additionally, we must pass these as part of the entity dict or meta.
- One approach: inject a temporary field in the entity dict like `_event_info` = `{"event_name": ..., "event_data": ...}`, which the workflow reads and removes after processing.
- This is a workaround to pass contextual data to the workflow function during update.

---

### Here is the updated complete code with these changes:

```python
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

# Data classes for request validation
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


# In-memory history store (should be ideally externalized)
entity_histories = {}

# External API URL for example (replace with real Trino or relevant API)
EXTERNAL_API_URL = "https://api.agify.io"  # Mock external data source


def create_entity_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# Workflow function for 'entity' entity_model on creation
async def process_entity(entity: dict) -> dict:
    """
    Initial workflow function applied on entity creation.
    Add created_at timestamp.
    """
    entity_data = entity.get("data", {})
    entity_data["created_at"] = now_iso()
    entity["data"] = entity_data
    return entity


# Workflow function to process events on an entity during update
async def process_entity_event(entity: dict) -> dict:
    """
    Workflow function applied asynchronously during update_item call.
    Expects event info in temporary '_event_info' key inside entity.
    Modifies entity in place accordingly.
    """
    event_info = entity.pop("_event_info", None)
    if not event_info:
        # No event info, nothing to do
        return entity

    event_name = event_info.get("event_name")
    event_data = event_info.get("event_data", {})

    current_state = entity.get("current_state")
    workflow = entity.get("workflow", {})
    transitions = workflow.get("transitions", [])

    # Find valid transition for this event
    transition = next(
        (t for t in transitions if t.get("from") == current_state and t.get("event") == event_name),
        None,
    )

    if not transition:
        logger.info(f"No valid transition for event '{event_name}' from state '{current_state}'")
        new_state = current_state
    else:
        new_state = transition.get("to")

    # Query external data asynchronously
    results = await query_external_data(event_data)

    # Update entity state and data
    updated_data = entity.get("data", {})
    updated_data.update(event_data)
    updated_data.update(results)
    entity["data"] = updated_data
    entity["current_state"] = new_state
    entity["workflow_status"] = "updated"

    # Append history entry locally
    history_entry = {
        "timestamp": now_iso(),
        "event": event_name,
        "from_state": current_state,
        "to_state": new_state,
        "metadata": {"event_data": event_data, "external_results": results},
    }
    entity_id = entity.get("technical_id") or entity.get("id")
    if entity_id:
        entity_histories.setdefault(entity_id, []).append(history_entry)

    # Example: Add supplementary entity - raw event log (different model)
    raw_event_entity = {
        "event_name": event_name,
        "event_data": event_data,
        "entity_id": entity_id,
        "timestamp": now_iso(),
    }
    # Add supplementary entity asynchronously (don't await - fire and forget)
    asyncio.create_task(
        entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_event_log",
            entity_version=ENTITY_VERSION,
            entity=raw_event_entity,
        )
    )

    return entity


async def query_external_data(event_data: dict) -> dict:
    """
    Query external API with event_data.
    This example uses agify.io to mock Trino queries via HTTP.
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
            "current_state": workflow.get("states", [None])[0],
            "workflow": workflow,
            "workflow_status": "created",
            "data": initial_data.copy(),
        }

        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_dict,
            workflow=process_entity,  # Creation workflow
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

        # Inject event info into entity for workflow processing
        entity["_event_info"] = {"event_name": event_name, "event_data": event_data}

        # Update entity with event processing workflow
        # The process_entity_event workflow will handle state change, external queries, history, supplementary entities
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
```

---

### Explanation:

- **`process_entity`**: Runs on entity creation, initializes `created_at`.
- **`process_entity_event`**: Runs on entity update triggered by an event.
  - Reads `_event_info` from the entity dict (injected by the endpoint).
  - Computes the new state based on transitions and event.
  - Queries external data asynchronously.
  - Updates entity data/state in-place.
  - Adds a history entry locally.
  - Creates a supplementary entity asynchronously for raw event logs.
- The event endpoint now only fetches the entity, injects `_event_info`, and calls `update_item` with the workflow.
- Fire-and-forget supplementary entity creation is done inside the workflow function using `asyncio.create_task`.

---

### Benefits:

- Endpoint handlers are minimal, only handling HTTP and validation.
- All entity state transitions, external API calls, event processing logic are inside workflow functions.
- Avoids infinite recursion since the workflow does not call update/add for the current entity.
- Supports asynchronous workflows, including external queries and supplementary entities.
- Easy to extend workflows with additional logic without touching endpoints.

---

Let me know if you want me to help with adding unit tests or further splitting logic!