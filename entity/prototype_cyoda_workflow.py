#!/usr/bin/env python
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
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

async def process_hello(entity: dict) -> dict:
    # Workflow function applied to the 'hello' entity before persistence.
    # It performs asynchronous tasks such as calling external APIs,
    # simulating processing delay, and updating the entity state.
    try:
        # Call external API to retrieve current UTC time
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            resp.raise_for_status()
            time_data = resp.json()
            current_time = time_data.get("utc_datetime", datetime.utcnow().isoformat())
        entity["requestedAt"] = current_time

        # Simulate processing delay
        await asyncio.sleep(2)

        # Call external API to get a joke
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.chucknorris.io/jokes/random")
            response.raise_for_status()
            joke_data = response.json()
            joke = joke_data.get("value")
        entity["joke"] = joke

        # Update entity status to completed and set completion timestamp
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        # In case of failure, update the entity status accordingly
        entity["status"] = "failed"
        logger.exception(e)
    return entity

@app.route("/hello", methods=["GET"])
async def get_hello():
    # GET /hello
    # Retrieves a "Hello World" message.
    return jsonify({"message": "Hello World"}), 200

# For POST requests, the route decorator must come first, then validate_request.
# This is a known workaround due to an issue in the quart-schema library.
@app.route("/hello", methods=["POST"])
@validate_request(Greeting)
async def post_hello(data: Greeting):
    # POST /hello
    # Invokes business logic to generate a greeting message.
    # It optionally accepts a JSON body with a 'name' field.
    # The workflow function performs asynchronous processing
    # and updates the entity state before it is persisted.
    try:
        name = data.name
        greeting = f"Hello, {name}" if name else "Hello World"

        # Prepare minimal entity data; further processing will be done by the workflow.
        job_data = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "name": data.name,
            "greeting": greeting
        }
        # Add the job record through the external entity service with workflow processing.
        # The process_hello function will be applied to the entity asynchronously
        # before it is persisted.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_hello
        )
        # Return only the technical_id in the response.
        return jsonify({"technical_id": job_id}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)