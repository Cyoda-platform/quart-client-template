from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# EntityTriggerRequest for POST /entity/trigger-workflow
@dataclass
class EntityTriggerRequest:
    entity_id: str
    event_type: str
    event_payload: Optional[Dict[str, Any]] = field(default_factory=dict)

# In-memory storage to mock persistence
entity_store: Dict[str, Dict] = {}

async def fetch_external_data(name: str) -> Dict:
    url = f"https://api.agify.io/?name={name}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return data
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching external data: {e}")
            return {}

async def process_entity(entity_data: Dict):
    entity_id = entity_data["entity_id"]
    event_payload = entity_data.get("event_payload", {})
    name = event_payload.get("name", "world")  # Default to 'world' if no name provided

    entity_store[entity_id]["status"] = "processing"
    entity_store[entity_id]["workflow_state"] = "started"

    external_data = await fetch_external_data(name)

    age = external_data.get("age")
    count = external_data.get("count")
    if age is not None:
        message = f"Hello {name.capitalize()}! Predicted age is {age} based on {count} samples."
    else:
        message = f"Hello {name.capitalize()}!"

    entity_store[entity_id].update({
        "workflow_state": "completed",
        "last_message": message,
        "status": "done",
        "updated_at": datetime.utcnow().isoformat()
    })
    logger.info(f"Processed entity {entity_id} with message: {message}")

# POST endpoint: validation must come after route decorator (issue workaround)
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

    asyncio.create_task(process_entity({
        "entity_id": entity_id,
        "event_type": event_type,
        "event_payload": event_payload
    }))

    return jsonify({
        "status": "success",
        "workflow_state": entity_store[entity_id]["workflow_state"],
        "message": "Hello World processing started"
    }), 202

# GET endpoint: no validation needed, no body, no query parameters
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
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
