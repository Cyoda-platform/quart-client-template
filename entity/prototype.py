```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import httpx
import asyncio
import logging
from datetime import datetime

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a Quart app
app = Quart(__name__)
QuartSchema(app)

# In-memory cache for demonstration purposes
entity_job = {}

@dataclass
class HelloRequest:
    name: str

@dataclass
class CalculateRequest:
    operation: str
    numbers: list

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

# Example of an external API call (Mock)
async def process_entity(entity_id, data):
    # TODO: Implement the processing logic and call to a real external API
    try:
        async with httpx.AsyncClient() as client:
            # Example API call (mocked URL)
            response = await client.post("https://api.example.com/process", json=data)
            response.raise_for_status()
            logger.info(f"Processed entity {entity_id}: {response.json()}")
    except Exception as e:
        logger.exception(e)

@app.route('/start_process', methods=['POST'])
@validate_request(HelloRequest)  # Validation must be last in POST
async def start_process(data: HelloRequest):
    entity_id = data.name  # Using name as entity_id for demonstration
    requested_at = datetime.now()
    entity_job[entity_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_id, data.__dict__))

    return jsonify({"status": "processing", "entity_id": entity_id})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```