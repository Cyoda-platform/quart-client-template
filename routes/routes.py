from dataclasses import dataclass
from typing import Dict, Any

import asyncio
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

EXTERNAL_API_URL = "https://jsonplaceholder.typicode.com/todos/1"

@dataclass
class TriggerWorkflowRequest:
    event_type: str
    payload: Dict[str, Any]

@dataclass
class ProcessDataRequest:
    input_data: Dict[str, Any]

@app.route("/api/entity/<string:entity_id>/trigger", methods=["POST"])
@validate_request(TriggerWorkflowRequest)
async def trigger_workflow(entity_id, data: TriggerWorkflowRequest):
    entity_data = {
        "workflow_type": "trigger_workflow",
        "event_type": data.event_type,
        "payload": data.payload,
        "status": "queued",
        "entity_id": entity_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            technical_id=entity_id,
            meta={},
        )
        entity_id_returned = entity_id
    except Exception:
        entity_id_returned = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )

    return jsonify(
        {
            "status": "success",
            "message": "Workflow triggered",
            "entity_id": entity_id_returned,
        }
    )

@app.route("/api/entity/<string:entity_id>/state", methods=["GET"])
async def get_entity_state(entity_id):
    try:
        state = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception:
        return jsonify({"status": "error", "message": "Entity not found"}), 404

    response = {
        "entity_id": entity_id,
        "current_state": state.get("current_state"),
        "data": state.get("result"),
        "last_updated": state.get("updated_at"),
        "status": state.get("status"),
    }
    return jsonify(response)

@app.route("/api/entity/<string:entity_id>/process", methods=["POST"])
@validate_request(ProcessDataRequest)
async def submit_data_for_processing(entity_id, data: ProcessDataRequest):
    entity_data = {
        "workflow_type": "process_data",
        "input_data": data.input_data,
        "status": "queued",
        "entity_id": entity_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            technical_id=entity_id,
            meta={},
        )
        entity_id_returned = entity_id
    except Exception:
        entity_id_returned = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )

    return jsonify({"status": "success", "message": "Processing started", "entity_id": entity_id_returned})

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)