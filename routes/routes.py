from common.grpc_client.grpc_client import grpc_stream
from dataclasses import dataclass
import logging
from datetime import datetime
import uuid
import asyncio

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CatRequest:
    type: str = "fact"  # Optional, default to "fact"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

@app.route("/api/cats/hello-world", methods=["POST"])
@validate_request(CatRequest)
async def post_hello_world(data: CatRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    initial_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
        "type": data.type,
        "resultId": job_id
    }

    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="CatJob",
            entity_version=ENTITY_VERSION,
            entity=initial_data,
            )
    except Exception:
        logger.exception("Failed to add CatJob entity")
        return jsonify({
            "status": "error",
            "message": "Failed to start processing"
        }), 500

    return jsonify({
        "status": "success",
        "message": "Hello World with cat data fetching started",
        "resultId": job_id
    }), 202

@app.route("/api/cats/result/<result_id>", methods=["GET"])
async def get_result(result_id):
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model="CatJob",
            entity_version=ENTITY_VERSION,
            technical_id=result_id
        )
        if not data:
            return jsonify({"error": "Result not found"}), 404

        status = data.get("status", "")
        if status == "processing":
            return jsonify({"status": "processing"}), 202
        if status == "failed":
            return jsonify({"status": "failed", "error": data.get("result", {}).get("error")}), 500

        return jsonify(data.get("result")), 200

    except Exception:
        logger.exception("Failed to retrieve CatJob result")
        return jsonify({"error": "Failed to retrieve result"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)