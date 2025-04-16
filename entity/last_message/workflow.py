import asyncio
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a Quart application
app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory cache for storing the last message
last_message_cache = {}

@dataclass
class HelloRequest:
    name: str

@dataclass
class LastMessageResponse:
    last_message: str

async def process_hello_message(entity_data):
    # Generate the hello message
    entity_data['message'] = f"Hello, {entity_data['name']}!"
    
    # Log the message generation
    logger.info(f"Generated message: {entity_data['message']}")

@app.route('/api/hello', methods=['POST'])
@validate_request(HelloRequest)
async def say_hello(data: HelloRequest):
    entity_data = {'name': data.name}
    
    await process_hello_message(entity_data)
    last_message_cache['last_message'] = entity_data['message']
    await process_last_message(entity_data)

    return jsonify({"message": entity_data['message']})

@app.route('/api/hello', methods=['GET'])
@validate_querystring(HelloRequest)
async def get_last_message():
    last_message = last_message_cache.get('last_message', "No message generated yet.")
    
    return jsonify({"last_message": last_message})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)