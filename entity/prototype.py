```python
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

@app.route('/api/hello', methods=['POST'])
@validate_request(HelloRequest)  # Validation is last for POST requests
async def say_hello(data: HelloRequest):
    name = data.name

    # Generate the hello message
    message = f"Hello, {name}!"
    
    # Store the last message in the cache
    last_message_cache['last_message'] = message
    
    # Log the message generation
    logger.info(f"Generated message: {message}")

    return jsonify({"message": message})

@app.route('/api/hello', methods=['GET'])
@validate_querystring(HelloRequest)  # Validation must be first for GET requests
async def get_last_message():
    # Retrieve the last message from the cache
    last_message = last_message_cache.get('last_message', "No message generated yet.")
    
    return jsonify({"last_message": last_message})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```