from common.grpc_client.grpc_client import grpc_stream

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import asyncio
import logging
import datetime
import uuid
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@dataclass
class HelloResponse:
    message: str

@dataclass
class ProcessInput:
    input_data: str

@app.route("/hello", methods=["GET"])
@validate_querystring(HelloResponse)  # Workaround: validation must be first for GET requests
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route("/process", methods=["POST"])
@validate_request(ProcessInput)  # Validate request body against ProcessInput schema
async def process():
    data = await request.get_json()
    input_data = data.get("input_data")

    if not input_data:
        return jsonify({"error": "Invalid input"}), 400

    job_id = str(uuid.uuid4())

    # Prepare the entity with the input data
    entity = {"input_data": input_data}  # Adjust as needed

    # Call to external service to add the job
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_name",
            entity_version=ENTITY_VERSION,
            entity=entity,
            )
        
        logger.info(f"Created job {job_id} for input: {input_data}")
        return jsonify({"job_id": job_id}), 200
    except Exception as e:
        logger.exception("Failed to create job in external service")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
