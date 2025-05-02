from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import asyncio
import httpx
import logging
from quart import Quart, jsonify, request
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

@dataclass
class InputData:
    query: str  # expecting a simple string query for external API


async def fetch_external_data(query: str) -> Dict:
    """
    Example real external API call.
    Using DuckDuckGo Instant Answer API as a public free API for demo:
    https://api.duckduckgo.com/?q=apple&format=json
    """
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json"}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            # Extract a brief abstract text as example "calculation"
            abstract = data.get("AbstractText", "")
            return {"abstract": abstract}
        except Exception as e:
            logger.exception(e)
            return {"error": str(e)}


async def process_entity(job_id: str, input_data: dict):
    """
    Simulate business logic:
    - Fetch external data based on input query
    - Update entity_service item with results and status
    """
    try:
        query = input_data.get("query")
        if not query:
            raise ValueError("Missing required field 'query' in inputData")

        logger.info(f"Processing job {job_id} with query: {query}")

        external_data = await fetch_external_data(query)

        if "error" in external_data:
            update_data = {
                "status": "failed",
                "result": {"error": external_data["error"]},
                "query": query,
                "processedAt": datetime.utcnow().isoformat() + "Z",
            }
        else:
            update_data = {
                "status": "completed",
                "result": {
                    "query": query,
                    "externalSummary": external_data["abstract"],
                    "processedAt": datetime.utcnow().isoformat() + "Z",
                },
            }

        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={},
        )

        logger.info(f"Job {job_id} completed with status {update_data['status']}")

    except Exception as e:
        logger.exception(e)
        update_data = {
            "status": "failed",
            "result": {"error": str(e)},
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                entity=update_data,
                technical_id=job_id,
                meta={},
            )
        except Exception as ex:
            logger.exception(ex)


@app.route("/process-data", methods=["POST"])
@validate_request(InputData)  # Validation last for POST requests (issue workaround)
async def post_process_data(data: InputData):
    input_data = {"query": data.query}

    # Create a new job entity with initial status 'processing'
    initial_data = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }

    try:
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=initial_data,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create job"}), 500

    asyncio.create_task(process_entity(job_id, input_data))

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
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)