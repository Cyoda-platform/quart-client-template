```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches for entities and processing results
entity_store = {}
result_store = {}

# Simulated external data source URL (public API for demo)
EXTERNAL_API_URL = "https://jsonplaceholder.typicode.com/todos/1"  # Example external API


@app.route("/entity", methods=["POST"])
async def create_entity():
    try:
        data = await request.get_json()
        entity_type = data.get("entityType")
        attributes = data.get("attributes", {})

        if not entity_type:
            return jsonify({"error": "entityType is required"}), 400

        entity_id = str(uuid.uuid4())
        entity_store[entity_id] = {
            "type": entity_type,
            "attributes": attributes,
            "createdAt": datetime.utcnow().isoformat(),
            "status": "workflow triggered",
        }

        # Fire and forget example workflow (could be expanded later)
        await asyncio.create_task(dummy_workflow(entity_id))

        return jsonify({"entityId": entity_id, "status": "workflow triggered"}), 200

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/process", methods=["POST"])
async def process_data():
    try:
        data = await request.get_json()
        entity_id = data.get("entityId")
        input_data = data.get("inputData", {})

        if not entity_id or entity_id not in entity_store:
            return jsonify({"error": "Invalid or missing entityId"}), 400

        result_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        result_store[result_id] = {"status": "processing", "requestedAt": requested_at}

        # Fire and forget the processing task
        await asyncio.create_task(process_entity(result_id, entity_id, input_data))

        return jsonify({"resultId": result_id, "processingStatus": "processing"}), 200

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/results/<result_id>", methods=["GET"])
async def get_results(result_id):
    try:
        if result_id not in result_store:
            return jsonify({"error": "Result not found"}), 404

        result = result_store[result_id]

        # If processing is not done yet, inform user
        if result.get("status") != "completed":
            return jsonify({"resultId": result_id, "status": result.get("status")}), 202

        return jsonify({"resultId": result_id, "data": result.get("data", {})}), 200

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


async def dummy_workflow(entity_id: str):
    """Example placeholder workflow triggered on entity creation."""
    try:
        # TODO: Implement real workflow logic and state transitions here
        logger.info(f"Workflow started for entity {entity_id}")
        await asyncio.sleep(1)  # simulate work
        logger.info(f"Workflow completed for entity {entity_id}")
    except Exception as e:
        logger.exception(e)


async def process_entity(result_id: str, entity_id: str, input_data: dict):
    """
    Business logic that:
    - Calls an external API
    - Performs simple calculation / transformation
    - Stores results in result_store
    """
    try:
        async with httpx.AsyncClient() as client:
            # Call external real API
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            external_data = response.json()

        # TODO: Replace below sample calculation with your real business logic
        calculated_value = len(input_data) + len(external_data)

        result_store[result_id].update(
            {
                "status": "completed",
                "completedAt": datetime.utcnow().isoformat(),
                "data": {
                    "entityId": entity_id,
                    "inputSummary": input_data,
                    "externalDataSample": external_data,
                    "calculatedValue": calculated_value,
                },
            }
        )
        logger.info(f"Processing completed for result {result_id}")

    except Exception as e:
        logger.exception(e)
        result_store[result_id].update({"status": "failed", "error": str(e)})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
