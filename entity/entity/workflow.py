from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class EntityTriggerRequest:
    entity_id: str
    event_type: str
    event_payload: Optional[Dict[str, Any]] = field(default_factory=dict)

entity_store: Dict[str, Dict] = {}

async def process_initialize(entity: Dict[str, Any]):
    now_iso = datetime.utcnow().isoformat()
    entity.setdefault("workflow_state", "initialized")
    entity.setdefault("status", "pending")
    entity.setdefault("created_at", now_iso)
    entity["updated_at"] = now_iso

async def process_start(entity: Dict[str, Any]):
    entity["workflow_state"] = "started"
    entity["status"] = "processing"
    entity["updated_at"] = datetime.utcnow().isoformat()

async def process_fetch_external_data(entity: Dict[str, Any]) -> Dict[str, Any]:
    event_payload = entity.get("last_event_payload") or {}
    name = event_payload.get("name", "world")
    url = f"https://api.agify.io/?name={name}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching external data: {e}")
            return {}

async def process_finalize(entity: Dict[str, Any], external_data: Dict[str, Any]):
    event_payload = entity.get("last_event_payload") or {}
    name = event_payload.get("name", "world")
    age = external_data.get("age")
    count = external_data.get("count")

    if age is not None:
        message = f"Hello {name.capitalize()}! Predicted age is {age} based on {count} samples."
    else:
        message = f"Hello {name.capitalize()}!"

    entity["workflow_state"] = "completed"
    entity["last_message"] = message
    entity["status"] = "done"
    entity["updated_at"] = datetime.utcnow().isoformat()

async def process_error(entity: Dict[str, Any], e: Exception):
    entity["workflow_state"] = "error"
    entity["status"] = "error"
    entity["last_message"] = f"Processing failed: {str(e)}"
    entity["updated_at"] = datetime.utcnow().isoformat()
    logger.exception(f"Error in process_entity workflow for entity_id={entity.get('entity_id', '<unknown>')}: {e}")

@app.route('/entity/trigger-workflow', methods=['POST'])
@validate_request(EntityTriggerRequest)
async def trigger_workflow(data: EntityTriggerRequest):
    entity_id = data.entity_id
    event_type = data.event_type
    event_payload = data.event_payload or {}

    now_iso = datetime.utcnow().isoformat()
    entity_store.setdefault(entity_id, {
        "entity_id": entity_id,
        "workflow_state": "initialized",
        "last_message": "",
        "status": "pending",
        "created_at": now_iso,
        "updated_at": now_iso
    })

    entity_store[entity_id]["last_event_type"] = event_type
    entity_store[entity_id]["last_event_payload"] = event_payload

    asyncio.create_task(process_entity(entity_store[entity_id]))

    return jsonify({
        "status": "success",
        "workflow_state": entity_store[entity_id]["workflow_state"],
        "message": "Hello World processing started"
    }), 202

@app.route('/entity/<string:entity_id>/status', methods=['GET'])
async def get_entity_status(entity_id):
    entity = entity_store.get(entity_id)
    if not entity:
        return jsonify({"status": "error", "message": "Entity not found"}), 404

    return jsonify({
        "entity_id": entity_id,
        "workflow_state": entity.get("workflow_state", ""),
        "last_message": entity.get("last_message", "")
    }), 200

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)