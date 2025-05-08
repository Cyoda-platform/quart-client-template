from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class EntityTriggerRequest:
    entity_id: str
    event_type: str
    event_payload: Optional[Dict[str, Any]] = field(default_factory=dict)

async def fetch_external_data(name: str) -> Dict[str, Any]:
    url = f"https://api.agify.io/?name={name}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching external data: {e}")
            return {}

async def process_entity(entity: Dict[str, Any]):
    """
    Workflow function that modifies the entity in-place before persistence.
    It performs async operations and updates entity state accordingly.
    """
    entity_id = entity.get("entity_id", "<unknown>")
    try:
        # Initialize missing fields if any
        now_iso = datetime.utcnow().isoformat()
        entity.setdefault("workflow_state", "initialized")
        entity.setdefault("status", "pending")
        entity.setdefault("created_at", now_iso)
        entity["updated_at"] = now_iso

        # Update entity state to processing
        entity["workflow_state"] = "started"
        entity["status"] = "processing"
        entity["updated_at"] = datetime.utcnow().isoformat()

        # Extract event payload info
        event_payload = entity.get("last_event_payload") or {}
        name = event_payload.get("name", "world")

        # Fetch external data asynchronously
        external_data = await fetch_external_data(name)
        age = external_data.get("age")
        count = external_data.get("count")

        if age is not None:
            message = f"Hello {name.capitalize()}! Predicted age is {age} based on {count} samples."
        else:
            message = f"Hello {name.capitalize()}!"

        # Finalize entity updates
        entity["workflow_state"] = "completed"
        entity["last_message"] = message
        entity["status"] = "done"
        entity["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception(f"Error in process_entity workflow for entity_id={entity_id}: {e}")
        entity["workflow_state"] = "error"
        entity["status"] = "error"
        entity["last_message"] = f"Processing failed: {str(e)}"
        entity["updated_at"] = datetime.utcnow().isoformat()

@app.route('/entity/trigger-workflow', methods=['POST'])
@validate_request(EntityTriggerRequest)
async def trigger_workflow(data: EntityTriggerRequest):
    entity_id = data.entity_id
    now_iso = datetime.utcnow().isoformat()

    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve entity"}), 500

    if not entity:
        # Minimal new entity skeleton
        entity = {
            "entity_id": entity_id,
            "created_at": now_iso,
            "updated_at": now_iso,
            "status": "pending",
            "workflow_state": "initialized",
            "last_message": "",
        }

    # Update event info for the workflow function
    entity["last_event_type"] = data.event_type
    entity["last_event_payload"] = data.event_payload or {}
    entity["updated_at"] = now_iso

    try:
        # Persist entity with workflow applied before persistence
        if not await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        ):
            # Add new entity with workflow
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                entity=entity,
                workflow=process_entity
            )
        else:
            # Update existing entity with workflow
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                entity=entity,
                technical_id=entity_id,
                meta={},
                workflow=process_entity
            )
    except Exception as e:
        logger.exception(f"Failed to persist entity {entity_id} with workflow: {e}")
        return jsonify({"status": "error", "message": "Failed to process entity"}), 500

    return jsonify({
        "status": "success",
        "workflow_state": entity.get("workflow_state", ""),
        "message": "Hello World processing started"
    }), 202

@app.route('/entity/<string:entity_id>/status', methods=['GET'])
async def get_entity_status(entity_id: str):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve entity"}), 500

    if not entity:
        return jsonify({"status": "error", "message": "Entity not found"}), 404

    return jsonify({
        "entity_id": entity_id,
        "workflow_state": entity.get("workflow_state", ""),
        "last_message": entity.get("last_message", "")
    }), 200

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)