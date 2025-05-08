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