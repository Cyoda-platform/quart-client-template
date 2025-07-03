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

# Request schemas
@dataclass
class WorkflowTriggerRequest:
    event: str
    payload: dict

@dataclass
class ListQuery:
    state: str
    limit: int
    offset: int

# In-memory cache for workflow states only (entity data replaced by entity_service)
entity_jobs: Dict[str, Dict[str, Any]] = {}

EXTERNAL_API_BASE = "https://api.agify.io"

async def fetch_external_data(name: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_BASE, params={"name": name})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(e)
            return {"error": "Failed to fetch external data"}

async def process_workflow(entity_id: str, event: str, payload: dict):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
        current_state = entity.get("current_state", "Created") if entity else "Created"
        new_state = "Processing"
        result = {}

        if event == "predict_age" and "name" in payload:
            external_result = await fetch_external_data(payload["name"])
            if "error" not in external_result:
                result = external_result
                new_state = "Completed"
            else:
                new_state = "Failed"
                result = {"error": "External API failure"}
        else:
            new_state = "Failed"
            result = {"error": "Unsupported event or missing payload"}  # TODO: extend for more events

        updated_entity = {"current_state": new_state, "data": result}
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=updated_entity,
            technical_id=entity_id,
            meta={}
        )
        logger.info(f"Entity {entity_id} updated to state {new_state}")

    except Exception as e:
        logger.exception(e)
        failed_entity = {"current_state": "Failed", "data": {"error": str(e)}}
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity",
                entity_version=ENTITY_VERSION,
                entity=failed_entity,
                technical_id=entity_id,
                meta={}
            )
        except Exception as inner_e:
            logger.exception(inner_e)

@app.route("/api/entity/<string:entity_id>/workflow/trigger", methods=["POST"])
@validate_request(WorkflowTriggerRequest)  # validation last for POST (workaround issue)
async def trigger_workflow(data: WorkflowTriggerRequest, entity_id):
    requested_at = datetime.utcnow().isoformat()
    job_id = f"{entity_id}-{requested_at}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    asyncio.create_task(process_workflow(entity_id, data.event, data.payload))

    # Retrieve current_state and result from entity_service
    entity = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="entity",
        entity_version=ENTITY_VERSION,
        technical_id=entity_id
    )
    current_state = entity.get("current_state", "Created") if entity else "Created"
    result = entity.get("data", {}) if entity else {}

    return jsonify({
        "status": "accepted",
        "job_id": job_id,
        "workflow_state": current_state,
        "result": result
    }), 202

@app.route("/api/entity/<string:entity_id>/state", methods=["GET"])
async def get_entity_state(entity_id):
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

@validate_querystring(ListQuery)  # validation first for GET (workaround issue)
@app.route("/api/entity/list", methods=["GET"])
async def list_entities():
    state_filter = request.args.get("state")
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", type=int, default=0)

    try:
        all_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to retrieve entities"}), 500

    filtered = []
    for entity in all_entities:
        eid = entity.get("id")
        current_state = entity.get("current_state", "Created")
        if state_filter and current_state != state_filter:
            continue
        filtered.append({"entity_id": str(eid), "current_state": current_state})

    if limit is not None:
        filtered = filtered[offset:offset + limit]
    else:
        filtered = filtered[offset:]

    return jsonify({"entities": filtered})

if __name__ == '__main__':
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)