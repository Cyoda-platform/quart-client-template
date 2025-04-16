```python
import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a Quart application
app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class HelloRequest:
    name: str

@dataclass
class LastMessageResponse:
    last_message: str

async def process_last_message(entity_data):
    # Modify the entity data as needed before persistence
    entity_data['processed'] = True  # Example modification

    # Log the processing of entity data for tracking or debugging
    logger.info(f"Processing entity data: {entity_data}")

    # Fire and forget async task can be handled here if needed
    # Example async operation can be added if required
    # await some_async_function(entity_data)

    return entity_data

@app.route('/api/hello', methods=['POST'])
@validate_request(HelloRequest)  # Validation is last for POST requests
async def say_hello(data: HelloRequest):
    name = data.name

    # Generate the hello message
    message = f"Hello, {name}!"

    # Prepare data to be stored in the external service
    entity_data = {"message": message}

    # Store the last message using the external service
    try:
        last_message_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="last_message",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_last_message  # Pass the workflow function
        )
        
        # Return the response with the generated message and its ID
        return jsonify({"message": message, "id": last_message_id})
    except Exception as e:
        logger.exception("Failed to store the message: %s", e)
        return jsonify({"error": "Failed to store the message"}), 500

async def process_get_last_message(entity_data):
    # Logic for processing and retrieving the last message can be added here
    try:
        last_message_items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="last_message",
            entity_version=ENTITY_VERSION,
        )

        if last_message_items:
            last_message = last_message_items[-1].get('message', "No message generated yet.")
        else:
            last_message = "No message generated yet."

        entity_data['last_message'] = last_message  # Add last message to entity data
    except Exception as e:
        logger.exception("Failed to retrieve last messages: %s", e)
        entity_data['last_message'] = "Error retrieving messages"

    return entity_data

@app.route('/api/hello', methods=['GET'])
@validate_querystring(HelloRequest)  # Validation must be first for GET requests
async def get_last_message():
    entity_data = {}  # Create an empty entity data structure
    try:
        # Use workflow function to process and retrieve the last message
        await process_get_last_message(entity_data)
        
        return jsonify({"last_message": entity_data.get('last_message', "No message generated yet.")})
    except Exception as e:
        logger.exception("Failed to process get last message: %s", e)
        return jsonify({"error": "Failed to retrieve the message"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```