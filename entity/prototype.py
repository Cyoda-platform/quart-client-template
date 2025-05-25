from dataclasses import dataclass
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: due to validate_request defect, validation first for GET and last for POST

@dataclass
class EntityRequest:
    entityType: str
    event: Optional[str] = None

@dataclass
class EntitiesQuery:
    entityType: Optional[str] = None
    state: Optional[str] = None

# In-memory async-safe cache for entities
entity_store: Dict[str, Dict[str, Any]] = {}
entity_store_lock = asyncio.Lock()

@app.route("/entity", methods=["POST"])
@validate_request(EntityRequest)  # POST: validate_request last due to library defect
async def create_entity(data: EntityRequest):
    raw = await request.get_json()
    entity_type = data.entityType
    event = data.event
    entity_data = raw.get("data", {})

    entity_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    async with entity_store_lock:
        entity_store[entity_id] = {
            "entityId": entity_id,
            "entityType": entity_type,
            "state": "processing",
            "data": entity_data,
            "createdAt": requested_at,
            "lastUpdated": requested_at,
            "event": event,
        }

    asyncio.create_task(process_entity(entity_id, entity_type, entity_data, event))

    return jsonify({
        "entityId": entity_id,
        "status": "processing",
        "message": f"Entity {entity_type} creation started, workflow event: {event}"
    })

async def process_entity(entity_id: str, entity_type: str, data: Dict[str, Any], event: Any):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            joke_resp = await client.get("https://v2.jokeapi.dev/joke/Any?type=single")
            joke_resp.raise_for_status()
            joke_data = joke_resp.json()
            joke_text = joke_data.get("joke", "No joke found")

        new_state = "completed"
        enriched_data = dict(data)
        enriched_data["externalInfo"] = {"joke": joke_text}
        if event:
            enriched_data["lastEventProcessed"] = event

        async with entity_store_lock:
            entity_store[entity_id].update({
                "state": new_state,
                "data": enriched_data,
                "lastUpdated": datetime.utcnow().isoformat(),
            })

        logger.info(f"Entity {entity_id} processed successfully.")

    except Exception as e:
        logger.exception(f"Failed to process entity {entity_id}: {e}")
        async with entity_store_lock:
            entity_store[entity_id].update({
                "state": "error",
                "lastUpdated": datetime.utcnow().isoformat(),
                "error": str(e)
            })

@app.route("/entity/<entity_id>", methods=["GET"])
async def get_entity(entity_id):
    async with entity_store_lock:
        entity = entity_store.get(entity_id)

    if not entity:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404

    return jsonify(entity)

@validate_querystring(EntitiesQuery)  # GET: validate_querystring first due to library defect
@app.route("/entities", methods=["GET"])
async def list_entities():
    entity_type = request.args.get("entityType")
    state = request.args.get("state")

    async with entity_store_lock:
        entities = list(entity_store.values())

    if entity_type:
        entities = [e for e in entities if e.get("entityType") == entity_type]
    if state:
        entities = [e for e in entities if e.get("state") == state]

    response = [
        {
            "entityId": e["entityId"],
            "entityType": e["entityType"],
            "state": e["state"]
        }
        for e in entities
    ]

    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)