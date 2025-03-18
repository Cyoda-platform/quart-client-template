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
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Import required external service and constants
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass definition for POST request payload.
@dataclass
class Greeting:
    name: Optional[str] = None

async def process_entity(job_id: str, data: dict):
    """
    Background task to process the entity.
    This simulates processing delay and external API call.
    Afterwards, it updates the job status via the external entity service.
    """
    try:
        logger.info(f"Started processing job {job_id} with data: {data}")
        # Simulate processing delay
        await asyncio.sleep(2)
        # Example: Call an external API from within the background processing task.
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.chucknorris.io/jokes/random")
            response.raise_for_status()
            joke_data = response.json()
            logger.info(f"Job {job_id} external API response: {joke_data.get('value')}")
        # Update the job record with completed status using the external service
        update_data = {"status": "completed", "completedAt": datetime.utcnow().isoformat()}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Completed processing job {job_id}")
    except Exception as e:
        update_data = {"status": "failed"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )
        logger.exception(e)

@app.route("/hello", methods=["GET"])
async def get_hello():
    """
    GET /hello
    Retrieves a "Hello World" message.
    """
    return jsonify({"message": "Hello World"}), 200

# For POST requests, the route decorator must come first, then validate_request.
# This is a known workaround due to an issue in the quart-schema library.
@app.route("/hello", methods=["POST"])
@validate_request(Greeting)
async def post_hello(data: Greeting):
    """
    POST /hello
    Invokes business logic to generate a greeting message.
    It optionally accepts a JSON body with a 'name' field.
    Additionally, it performs an external API call and fires a background task.
    The response returns the technical_id from the external entity service.
    """
    try:
        name = data.name
        greeting = f"Hello, {name}" if name else "Hello World"

        # External API call to retrieve current UTC time
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            resp.raise_for_status()
            time_data = resp.json()
            current_time = time_data.get("utc_datetime", datetime.utcnow().isoformat())
            logger.info(f"External API UTC time: {current_time}")

        requested_at = datetime.utcnow().isoformat()
        # Prepare the entity data to be stored via the external service
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "name": data.name,
            "greeting": greeting
        }
        # Add the job record through the external entity service
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )
        # Fire-and-forget the background processing task
        asyncio.create_task(process_entity(job_id, job_data))
        # Return only the technical_id in the response
        return jsonify({"technical_id": job_id}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)