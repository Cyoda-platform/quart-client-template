Certainly! Below is your updated code with the `workflow` function added as a parameter to `entity_service.add_item` and implemented accordingly.

Key changes:
- Defined the workflow function `process_hello_world_job` which wraps the existing `process_entity` logic.
- Passed `workflow=process_hello_world_job` to `entity_service.add_item` in the `/api/hello-world/trigger` route.
- The `process_hello_world_job` function takes the entity data as the only argument and triggers the async processing logic.

```python
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
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


@dataclass
class EventData:
    message: str = None  # optional string, primitive type


async def fetch_external_greeting() -> str:
    """
    Fetch greeting message from a real external API.
    Using https://api.github.com/zen as a placeholder for an external API returning a string.
    TODO: Replace with a proper greeting API if desired.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/zen")
            response.raise_for_status()
            return response.text.strip()
    except Exception as e:
        logger.exception(e)
        return "Hello World!"  # Fallback greeting


async def process_entity(job_id: str, event_data: dict):
    """
    Simulates processing the entity workflow using a state machine.
    1. Fetch external data (greeting)
    2. Update state machine accordingly
    """
    try:
        # Retrieve job state from entity_service
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="hello_world_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
        )
        if not job:
            logger.error(f"Job {job_id} not found for processing")
            return

        job["status"] = STATE_PROCESSING
        job["startedAt"] = datetime.utcnow().isoformat()

        # Update job status to processing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="hello_world_job",
            entity_version=ENTITY_VERSION,
            entity=job,
            technical_id=job_id,
            meta={},
        )

        external_greeting = await fetch_external_greeting()

        user_msg = event_data.get("message") or external_greeting

        output = f"{user_msg}"

        job["status"] = STATE_COMPLETED
        job["completedAt"] = datetime.utcnow().isoformat()
        job["output"] = output

        # Update job with completed status and output
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="hello_world_job",
            entity_version=ENTITY_VERSION,
            entity=job,
            technical_id=job_id,
            meta={},
        )
    except Exception as e:
        logger.exception(e)
        try:
            job = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="hello_world_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
            )
            if job:
                job["status"] = "failed"
                job["error"] = str(e)
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="hello_world_job",
                    entity_version=ENTITY_VERSION,
                    entity=job,
                    technical_id=job_id,
                    meta={},
                )
        except Exception as ex:
            logger.exception(ex)


# Workflow function for the entity - must be named process_<entity_name> in underscore lowercase
async def process_hello_world_job(entity: dict):
    """
    Workflow function applied to the entity asynchronously before persistence.
    This function starts the processing task for the hello_world_job entity.
    """
    # Extract the technical id (workflow id) from the entity
    workflow_id = entity.get("technical_id") or entity.get("id")  # adjust if your id key is different
    if not workflow_id:
        logger.error("No technical_id found in entity for processing")
        return

    event_data = entity.get("event_data", {})

    # Fire and forget the processing task asynchronously
    asyncio.create_task(process_entity(workflow_id, event_data))


@app.route("/api/hello-world/trigger", methods=["POST"])
@validate_request(EventData)
async def trigger_hello_world(data: EventData):
    """
    POST endpoint to trigger the Hello World workflow.
    Accepts dynamic event_data JSON.
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
            workflow=process_hello_world_job,  # Pass the workflow function here
        )

        return jsonify({"workflow_id": workflow_id, "status": "initiated"})
    except Exception as e:
        logger.exception(e)
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
        }
        return jsonify(response)
    except Exception as e:
        logger.exception(e)
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
```

---

### Explanation:

- The new function `process_hello_world_job` is the workflow function for the entity model `"hello_world_job"`.
- It receives the entity dict, extracts the `technical_id` (or `id` if your schema differs) to know which job to process.
- It then starts the existing `process_entity` function asynchronously.
- The `workflow=process_hello_world_job` is passed to the `add_item` call, so that this workflow function gets applied asynchronously before persistence as required.
- The rest of your logic remains unchanged.

Let me know if you need help adjusting the `technical_id` field name or anything else!