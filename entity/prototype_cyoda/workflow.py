import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PrototypeCyodaTrigger:
    event_type: str
    payload: Optional[Dict[str, Any]] = None

entity_jobs: Dict[str, Dict[str, Any]] = {}

async def process_set_id_and_timestamp(entity: dict):
    if "id" not in entity:
        entity["id"] = str(uuid.uuid4())
    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"

async def process_fetch_external_uuid(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("https://httpbin.org/uuid")
            response.raise_for_status()
            data = response.json()
            entity["external_uuid"] = data.get("uuid")
    except Exception as e:
        logger.error(f"Error fetching external UUID: {e}")
        entity["external_uuid"] = None

async def process_mark_workflow_processed(entity: dict):
    entity["workflow_processed"] = True

@app.route("/prototype_cyoda/trigger", methods=["POST"])
@validate_request(PrototypeCyodaTrigger)
async def trigger_prototype_cyoda(data: PrototypeCyodaTrigger):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity = {
        "id": None,
        "event_type": data.event_type,
        "payload": data.payload or {},
        "requested_at": requested_at,
        "processed_at": None,
        "external_uuid": None,
        "workflow_processed": False
    }
    entity_jobs[job_id] = entity

    asyncio.create_task(process_prototype_cyoda(entity))

    return jsonify({
        "status": "started",
        "entity_id": job_id,
        "message": f"Prototype Cyoda workflow triggered for event '{data.event_type}'."
    })

@app.route("/prototype_cyoda/result/<entity_id>", methods=["GET"])
async def get_prototype_cyoda_result(entity_id):
    entity = entity_jobs.get(entity_id)
    if not entity:
        return jsonify({
            "entity_id": entity_id,
            "status": "not_found",
            "message": "Entity ID not found"
        }), 404

    return jsonify({
        "entity_id": entity_id,
        "event_type": entity["event_type"],
        "processed_at": entity["processed_at"],
        "external_uuid": entity["external_uuid"],
        "workflow_processed": entity["workflow_processed"]
    })

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)