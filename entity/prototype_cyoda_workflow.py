from dataclasses import dataclass
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

STATE_IDLE = "idle"
STATE_PROCESSING = "processing"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"


@dataclass
class EventData:
    message: str = None  # optional string, primitive type


async def fetch_external_greeting() -> str:
    """
    Fetch greeting message from an external API.
    Using https://api.github.com/zen as a placeholder for an external API returning a string.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/zen")
            response.raise_for_status()
            return response.text.strip()
    except Exception as e:
        logger.exception("Failed to fetch external greeting: %s", e)
        return "Hello World!"  # Fallback greeting


# Workflow function for 'hello_world_job' entity model
async def process_hello_world_job(entity: dict):
    """
    Workflow function applied to the 'hello_world_job' entity asynchronously before persistence.
    This function modifies the entity's state and output in place.
    """
    try:
        entity["status"] = STATE_PROCESSING
        entity["startedAt"] = datetime.utcnow().isoformat()

        external_greeting = await fetch_external_greeting()

        user_msg = entity.get("event_data", {}).get("message") or external_greeting

        output = f"{user_msg}"

        entity["status"] = STATE_COMPLETED
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["output"] = output

    except Exception as e:
        logger.exception("Workflow processing failed: %s", e)
        entity["status"] = STATE_FAILED
        entity["error"] = str(e)


@app.route("/api/hello-world/trigger", methods=["POST"])
@validate_request(EventData)
async def trigger_hello_world(data: EventData):
    """
    POST endpoint to trigger the Hello World workflow.
    Accepts event_data JSON.
    Returns workflow_id and status.
    """
    try:
        event_data = data.__dict__ if data else {}

        job_data = {
            "status": STATE_IDLE,
            "requestedAt": datetime.utcnow().isoformat(),
            "event_data": event_data,
        }

        workflow_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="hello_world_job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_hello_world_job,
        )

        return jsonify({"workflow_id": workflow_id, "status": "initiated"})

    except Exception as e:
        logger.exception("Failed to trigger workflow: %s", e)
        return jsonify({"error": "Failed to trigger workflow"}), 500


@app.route("/api/hello-world/result/<string:workflow_id>", methods=["GET"])
async def get_workflow_result(workflow_id: str):
    """
    GET endpoint to retrieve workflow result by workflow_id.
    Returns current state and output.
    """
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="hello_world_job",
            entity_version=ENTITY_VERSION,
            technical_id=workflow_id,
        )
        if not job:
            return jsonify({"error": "Workflow ID not found"}), 404

        response = {
            "workflow_id": workflow_id,
            "state": job.get("status", "unknown"),
            "output": job.get("output", None),
            "timestamp": job.get("completedAt") or job.get("requestedAt"),
            "error": job.get("error", None),
        }
        return jsonify(response)

    except Exception as e:
        logger.exception("Failed to retrieve workflow result: %s", e)
        return jsonify({"error": "Failed to retrieve workflow result"}), 500


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)