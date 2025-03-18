#!/usr/bin/env python
from common.grpc_client.grpc_client import grpc_stream
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

# External services and configurations
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Dataclass definition for POST request payload.
@dataclass
class Greeting:
    name: Optional[str] = None

@app.route("/hello", methods=["GET"])
async def get_hello():
    # GET /hello - Retrieves a simple greeting message.
    return jsonify({"message": "Hello World"}), 200

@app.route("/hello", methods=["POST"])
@validate_request(Greeting)
async def post_hello(data: Greeting):
    # POST /hello - Generates a greeting and persists an entity.
    try:
        name = data.name
        greeting_text = f"Hello, {name}" if name else "Hello World"
        job_data = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "name": name,
            "greeting": greeting_text
        }
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )
        return jsonify({"technical_id": job_id}), 200
    except Exception as e:
        logger.exception("Error in post_hello: %s", e)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/cats", methods=["POST"])
@validate_request(Greeting)
async def post_cats(data: Greeting):
    # POST /cats - Schedules a new integration job for the Cats API.
    try:
        name = data.name
        job_data = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "name": name,
            "integration": "cats_api"
        }
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=job_data
        )
        return jsonify({"technical_id": job_id}), 200
    except Exception as e:
        logger.exception("Error in post_cats: %s", e)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)