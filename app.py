from common.grpc_client.grpc_client import grpc_stream

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class GreetRequest:
    name: str

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route('/hello', methods=['GET'])
async def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/greet', methods=['POST'])
@validate_request(GreetRequest)  # Validation for POST request
async def greet(data: GreetRequest):
    name = data.name.strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400

    # Log the request
    logger.info(f"Greet request received for name: {name}")

    # Prepare data for external service
    entity_data = {"name": name}

    # Call to external service to add the item
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greet_entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )
        logger.info(f"Entity job added with ID: {job_id}")
    except Exception as e:
        logger.exception("Error adding item to entity service")
        return jsonify({"error": "Failed to process the request."}), 500

    return jsonify({"message": f"Hello, {name}!", "job_id": job_id})

@app.route('/greet', methods=['GET'])
@validate_querystring(GreetRequest)  # Workaround: Validation first for GET request
async def greet_get():
    name = request.args.get('name')

    if not name:
        return jsonify({"error": "Name is required."}), 400

    # Log the request
    logger.info(f"Greet GET request received for name: {name}")

    message = f"Hello, {name}!"
    return jsonify({"message": message})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
