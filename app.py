from common.grpc_client.grpc_client import grpc_stream
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

# For POST requests, use the decorator order recommended by quart-schema.
@app.route("/hello", methods=["POST"])
@validate_request(Greeting)
async def post_hello(data: Greeting):
    # POST /hello - Generates a greeting and persists an entity after asynchronous workflow processing.
    try:
        name = data.name
        greeting_text = f"Hello, {name}" if name else "Hello World"

        # Minimal entity data; additional processing will be handled by the workflow.
        job_data = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "name": name,
            "greeting": greeting_text
        }

        # Persist the entity using the external service.
        # The process_hello workflow function is applied to the entity asynchronously before persistence.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="hello",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            )

        # Return only the technical identifier.
        return jsonify({"technical_id": job_id}), 200
    except Exception as e:
        logger.exception("Error in post_hello: %s", e)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)