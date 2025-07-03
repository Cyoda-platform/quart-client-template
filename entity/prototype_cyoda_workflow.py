import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class WorkflowTriggerRequest:
    event: str
    payload: dict

@dataclass
class ListQuery:
    state: str
    limit: int
    offset: int

@dataclass
class NewEntityRequest:
    data: dict

entity_jobs: Dict[str, Dict[str, Any]] = {}

EXTERNAL_API_BASE = "https://api.agify.io"

async def fetch_external_data(name: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_BASE, params={"name": name})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch external data for name={name}: {e}")
            return {"error": "Failed to fetch external data"}

async def process_entity(entity: dict) -> dict:
    # Initialize mandatory fields for new entity
    if "current_state" not in entity:
        entity["current_state"] = "Created"
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()
    # Ensure 'data' field exists as dict
    if "data" not in entity or not isinstance(entity["data"], dict):
        entity["data"] = {}
    return entity

async def process_entity_workflow_trigger(entity: dict) -> dict:
    # Extract and remove workflow trigger info
    trigger = entity.pop('_workflow_trigger', None)
    if not trigger:
        # No trigger, do nothing
        return entity

    event = trigger.get("event")
    payload = trigger.get("payload", {})

    # Use or initialize current_state
    current_state = entity.get("current_state", "Created")

    try:
        if event == "predict_age":
            name = payload.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                entity["current_state"] = "Failed"
                entity["data"] = {"error": "Missing or invalid 'name' in payload for predict_age event"}
                return entity

            entity["current_state"] = "Processing"

            # Fetch external data asynchronously
            external_result = await fetch_external_data(name.strip())

            if "error" in external_result:
                entity["current_state"] = "Failed"
                entity["data"] = external_result
            else:
                entity["current_state"] = "Completed"
                entity["data"] = external_result

        else:
            # Unsupported event
            entity["current_state"] = "Failed"
            entity["data"] = {"error": f"Unsupported event '{event}'"}

    except Exception as e:
        logger.exception(f"Error processing workflow event '{event}': {e}")
        entity["current_state"] = "Failed"
        entity["data"] = {"error": str(e)}

    return entity

@app.route("/api/entity", methods=["POST"])
@validate_request(NewEntityRequest)
async def add_entity(data: NewEntityRequest):
    try:
        entity_data = data.data
        if not isinstance(entity_data, dict):
            return jsonify({"status": "error", "message": "Entity data must be a dict"}), 400
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_entity
        )
        return jsonify({"status": "success", "entity_id": entity_id}), 201
    except Exception as e:
        logger.exception(f"Failed to add entity: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/api/entity/<string:entity_id>/workflow/trigger", methods=["POST"])
@validate_request(WorkflowTriggerRequest)
async def trigger_workflow(data: WorkflowTriggerRequest, entity_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
        if not entity:
            return jsonify({"status": "error", "message": "Entity not found"}), 404

        # Add workflow trigger info to entity
        entity['_workflow_trigger'] = {
            "event": data.event,
            "payload": data.payload
        }

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            workflow=process_entity_workflow_trigger
        )

        updated_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
        current_state = updated_entity.get("current_state", "Created")
        result = updated_entity.get("data", {})

        return jsonify({
            "status": "accepted",
            "entity_id": entity_id,
            "workflow_state": current_state,
            "result": result
        }), 202
    except Exception as e:
        logger.exception(f"Failed to trigger workflow for entity {entity_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/api/entity/<string:entity_id>/state", methods=["GET"])
async def get_entity_state(entity_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
        if not entity:
            return jsonify({"status": "error", "message": "Entity not found"}), 404

        return jsonify({
            "entity_id": entity_id,
            "current_state": entity.get("current_state", "Created"),
            "data": entity.get("data", {})
        })
    except Exception as e:
        logger.exception(f"Failed to get entity state for {entity_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@validate_querystring(ListQuery)
@app.route("/api/entity/list", methods=["GET"])
async def list_entities():
    try:
        state_filter = request.args.get("state")
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int, default=0)

        all_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION
        )
        filtered = []
        for entity in all_entities:
            eid = entity.get("id")
            current_state = entity.get("current_state", "Created")
            if state_filter and current_state != state_filter:
                continue
            filtered.append({"entity_id": str(eid), "current_state": current_state})

        if limit is not None and limit >= 0 and offset >= 0:
            filtered = filtered[offset:offset + limit]
        else:
            filtered = filtered[offset:]

        return jsonify({"entities": filtered})
    except Exception as e:
        logger.exception(f"Failed to list entities: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)