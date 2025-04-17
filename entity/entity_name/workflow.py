from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import asyncio
import logging
import datetime
import uuid

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for jobs
entity_job = {}

@dataclass
class HelloResponse:
    message: str

@dataclass
class ProcessInput:
    input_data: str

async def process_mark_entity_as_processed(entity):
    entity["processed"] = True

async def process_add_timestamp(entity):
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()

async def process_simulate_processing(entity):
    # Simulate some asynchronous processing
    await asyncio.sleep(5)

@app.route("/hello", methods=["GET"])
@validate_querystring(HelloResponse)  # Workaround: validation must be first for GET requests
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route("/process", methods=["POST"])
async def process():
    data = await request.get_json()
    input_data = data.get("input_data")

    if not input_data:
        return jsonify({"error": "Invalid input"}), 400

    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": requested_at
    }

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_job[job_id]))

    logger.info(f"Created job {job_id} for input: {input_data}")
    return jsonify({"job_id": job_id}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)