from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass
import logging
import asyncio

app = Quart(__name__)
QuartSchema(app)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# In-memory cache to mock persistence
entity_job = {}

@dataclass
class GreetRequest:
    name: str

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

    # Mocking external processing as a fire-and-forget task
    requested_at = datetime.now()
    job_id = len(entity_job) + 1
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at, "name": name}

    # Fire and forget the processing task
    await asyncio.create_task(process_entity(entity_job[job_id]))

    message = f"Hello, {name}!"
    return jsonify({"message": message})

async def process_greet_entity(entity):
    # Process the greeting
    logger.info(f"Processing entity for {entity['name']}")
    entity['greeting'] = f"Hello, {entity['name']}!"
    await asyncio.sleep(2)  # Simulate a processing delay
    logger.info(f"Finished processing entity for {entity['name']}")

async def process_add_supplementary_entity(entity):
    # Simulate fetching or creating additional entities if needed.
    try:
        supplementary_entity_data = {"info": f"Additional info for {entity['name']}"}
        # Make sure to use a different entity_model for supplementary entities
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="supplementary_entity",
            entity_version=ENTITY_VERSION,
            entity=supplementary_entity_data,
            workflow=None  # No workflow for supplementary entities
        )
    except Exception as e:
        logger.exception("Error adding supplementary entity")
        # Handle the error appropriately, but do not prevent the main entity from being processed.

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)