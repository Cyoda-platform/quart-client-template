from common.grpc_client.grpc_client import grpc_stream
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import httpx
import logging
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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


@dataclass
class InputData:
    query: str  # expecting a simple string query for external API


@app.route("/process-data", methods=["POST"])
@validate_request(InputData)
async def post_process_data(data: InputData):
    entity_data = {
        "query": data.query,
    }

    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create job"}), 500

    return jsonify({"processId": job_id, "status": "processing"}), 202


@app.route("/results/<process_id>", methods=["GET"])
async def get_results(process_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=process_id,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": f"Failed to retrieve job with processId '{process_id}'"}), 500

    if not job:
        return jsonify({"error": f"No job found with processId '{process_id}'"}), 404

    response = {
        "processId": process_id,
        "status": job.get("status"),
        "result": job.get("result", None),
    }
    return jsonify(response), 200


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)