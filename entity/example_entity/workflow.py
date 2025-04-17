from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio

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

async def perform_additional_tasks(entity_data):
    # Example of an async operation that might involve fetching or processing data
    logger.info(f"Performing additional tasks for entity: {entity_data['name']}")
    await asyncio.sleep(1)

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

    result = None
    if data.operation == "add":
        result = sum(data.numbers)
    elif data.operation == "subtract":
        result = data.numbers[0] - data.numbers[1]
    else:
        return jsonify({"error": "Unsupported operation."}), 400

    return jsonify({"result": result})

@app.route('/start_process', methods=['POST'])
@validate_request(HelloRequest)  # Validation must be last in POST
async def start_process(data: HelloRequest):
    entity_id = data.name  # Using name as entity_id for demonstration
    entity_data = {'name': entity_id, 'processed': False}  # Initialize entity data
    await process_example_entity(entity_data)  # Call the processing function
    return jsonify({"status": "processing", "entity_id": entity_id})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)