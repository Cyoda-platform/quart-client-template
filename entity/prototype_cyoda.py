```python
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio
from datetime import datetime
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

    # Create a greeting message
    message = f"Hello, {name}!"

    # Prepare data for external service
    entity_data = {"name": name}
    
    # Call to external service to add the item
    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="greet_entity",
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        logger.info(f"Entity job added with ID: {job_id}")
    except Exception as e:
        logger.exception("Error adding item to entity service")
        return jsonify({"error": "Failed to process the request."}), 500

    return jsonify({"message": message, "job_id": job_id})

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

async def process_entity(entity_job, data):
    # Placeholder for processing logic
    logger.info(f"Processing entity for {data['name']}")
    await asyncio.sleep(5)  # Simulate a processing delay
    logger.info(f"Finished processing entity for {data['name']}")

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```