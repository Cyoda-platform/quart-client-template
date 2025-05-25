```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for entities: entity_id -> entity data
# Use asyncio.Lock to synchronize writes
entity_store: Dict[str, Dict[str, Any]] = {}
entity_store_lock = asyncio.Lock()


@app.route("/entity", methods=["POST"])
async def create_entity():
    """
    Create a new entity or trigger a workflow event.
    This may include calls to external APIs or calculations.
    """
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    entity_type = data.get("entityType")
    event = data.get("event")
    entity_data = data.get("data", {})

    if not entity_type:
        return jsonify({"error": "Missing entityType"}), 400

    entity_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    # Initialize entity with "processing" status and save minimal info
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

    # Fire-and-forget async processing task
    asyncio.create_task(process_entity(entity_id, entity_type, entity_data, event))

    return jsonify({
        "entityId": entity_id,
        "status": "processing",
        "message": f"Entity {entity_type} creation started, workflow event: {event}"
    })


async def process_entity(entity_id: str, entity_type: str, data: Dict[str, Any], event: Any):
    """
    Simulate processing workflow for entity:
    - Call external API(s)
    - Perform calculations
    - Update entity state and data
    """
    try:
        # Example external API call: fetch random joke from official JokeAPI
        # This is just a placeholder for any external data retrieval or calculation.
        # TODO: Replace with your domain-specific external APIs or logic as needed.
        async with httpx.AsyncClient(timeout=10) as client:
            joke_resp = await client.get("https://v2.jokeapi.dev/joke/Any?type=single")
            joke_resp.raise_for_status()
            joke_data = joke_resp.json()
            joke_text = joke_data.get("joke", "No joke found")

        # Simulate some business logic based on the event and external data
        new_state = "completed"
        enriched_data = dict(data)  # copy original data
        enriched_data["externalInfo"] = {"joke": joke_text}
        if event:
            enriched_data["lastEventProcessed"] = event

        # Update entity in store
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
    """
    Retrieve the current state or results of a specific entity.
    """
    async with entity_store_lock:
        entity = entity_store.get(entity_id)

    if not entity:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404

    return jsonify(entity)


@app.route("/entities", methods=["GET"])
async def list_entities():
    """
    List all entities or filter by type and/or state.
    """
    entity_type = request.args.get("entityType")
    state = request.args.get("state")

    async with entity_store_lock:
        entities = list(entity_store.values())

    if entity_type:
        entities = [e for e in entities if e.get("entityType") == entity_type]
    if state:
        entities = [e for e in entities if e.get("state") == state]

    # Return minimal info per entity as per spec
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
```
