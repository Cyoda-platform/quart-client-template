from common.grpc_client.grpc_client import grpc_stream

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a Quart app
app = Quart(__name__)
QuartSchema(app)

@dataclass
class HelloRequest:
    name: str

@dataclass
class CalculateRequest:
    operation: str
    numbers: list

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route('/hello', methods=['GET'])
@validate_querystring(HelloRequest)  # Workaround for validation order issue
async def get_hello():
    name = request.args.get('name', 'World')
    return jsonify({"message": f"Hello, {name}!"})

@app.route('/hello', methods=['POST'])
@validate_request(HelloRequest)  # Validation must be last in POST
async def post_hello(data: HelloRequest):
    return jsonify({"message": f"Hello, {data.name}!"})

@app.route('/calculate', methods=['POST'])
@validate_request(CalculateRequest)  # Validation must be last in POST
async def post_calculate(data: CalculateRequest):
    if len(data.numbers) != 2:
        return jsonify({"error": "Two numbers are required."}), 400

    result = await process_calculation(data.operation, data.numbers)
    return jsonify({"result": result})

async def process_calculation(operation, numbers):
    # Perform calculation based on the operation
    if operation == "add":
        return sum(numbers)
    elif operation == "subtract":
        return numbers[0] - numbers[1]
    else:
        raise ValueError("Unsupported operation.")

@app.route('/start_process', methods=['POST'])
@validate_request(HelloRequest)  # Validation must be last in POST
async def start_process(data: HelloRequest):
    entity_id = data.name  # Using name as entity_id for demonstration
    logger.info(f"Starting process for entity_id: {entity_id}")

    # Call to external entity_service to add item
    try:
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="example_entity",  # Replace with appropriate model name
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            )
        return jsonify({"status": "processing", "entity_id": id}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start process."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
