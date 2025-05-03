from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence for process jobs
entity_job = {}

# Example external API: https://api.agify.io/?name=michael (predicts age by name)
EXTERNAL_API_URL = "https://api.agify.io"

@dataclass
class InputData:
    name: str  # primitive type as per requirements

async def process_entity(entity_job, process_id, input_data):
    try:
        name = input_data.name
        async with httpx.AsyncClient() as client:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            api_data = response.json()

        result = {
            "name": name,
            "predicted_age": api_data.get("age"),
            "count": api_data.get("count"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        entity_job[process_id]["status"] = "completed"
        entity_job[process_id]["result"] = result
        logger.info(f"Processing completed for processId={process_id}")

    except Exception as e:
        entity_job[process_id]["status"] = "failed"
        entity_job[process_id]["result"] = None
        logger.exception(f"Error processing processId={process_id}: {e}")

# POST endpoint: validation last due to quart-schema library issue workaround
@app.route("/process-data", methods=["POST"])
@validate_request(InputData)
async def process_data(data: InputData):
    process_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[process_id] = {"status": "processing", "requestedAt": requested_at, "result": None}

    asyncio.create_task(process_entity(entity_job, process_id, data))

    return jsonify({
        "processId": process_id,
        "status": "processing",
        "result": None
    }), 202

# GET endpoint: validation first due to quart-schema library issue workaround
@app.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    job = entity_job.get(process_id)
    if not job:
        return jsonify({"error": "processId not found"}), 404

    return jsonify({
        "processId": process_id,
        "status": job["status"],
        "result": job["result"]
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
