import asyncio
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Dataclass definition for POST request payload.
@dataclass
class Greeting:
    name: Optional[str] = None

# In-memory storage for job processing
entity_jobs = {}

async def process_entity(job_id: str, data: dict):
    """
    Background task to process the entity.
    This is a placeholder for further business logic.
    TODO: Expand processing logic and persistence mechanism.
    """
    try:
        logger.info(f"Started processing job {job_id} with data: {data}")
        # Simulate processing delay
        await asyncio.sleep(2)
        # Example: Call an external API from within the background processing task.
        async with httpx.AsyncClient() as client:
            # Using a real API to fetch a random joke as part of the processing.
            response = await client.get("https://api.chucknorris.io/jokes/random")
            response.raise_for_status()
            joke_data = response.json()
            # TODO: Incorporate the joke into the processing result as needed.
            logger.info(f"Job {job_id} external API response: {joke_data.get('value')}")
        
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Completed processing job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(e)

@app.route('/hello', methods=['GET'])
async def get_hello():
    """
    GET /hello
    Retrieves a "Hello World" message.
    """
    return jsonify({"message": "Hello World"}), 200

# For POST requests, the route decorator must come first, then validate_request.
# This is a known workaround due to an issue in the quart-schema library.
@app.route('/hello', methods=['POST'])
@validate_request(Greeting)
async def post_hello(data: Greeting):
    """
    POST /hello
    Invokes business logic to generate a greeting message.
    It optionally accepts a JSON body with a 'name' field.
    Additionally, it performs an external API call and fires a background task.
    """
    try:
        name = data.name
        greeting = f"Hello, {name}" if name else "Hello World"
        
        # Example external API call to retrieve current UTC time
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            resp.raise_for_status()
            time_data = resp.json()
            current_time = time_data.get("utc_datetime", datetime.utcnow().isoformat())
            logger.info(f"External API UTC time: {current_time}")
        
        # Create a job entry in the local cache and fire-and-forget processing task.
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
        
        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, data.__dict__))
        
        return jsonify({"message": greeting}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)