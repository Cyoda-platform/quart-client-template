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
            abstract = data.get("AbstractText", "")
            return {"abstract": abstract}
        except Exception as e:
            logger.exception(e)
            return {"error": str(e)}


# Workflow function for 'entity_job' entity_model
async def process_entity_job(entity: dict) -> dict:
    """
    Workflow function applied to entity_job entities before persistence.
    This function:
    - expects 'query' field in entity
    - adds createdAt timestamp
    - fetches external data asynchronously
    - updates entity state with status/result fields
    """
    try:
        now_iso = datetime.utcnow().isoformat() + "Z"
        if "createdAt" not in entity:
            entity["createdAt"] = now_iso

        query = entity.get("query")
        if not query or not isinstance(query, str) or not query.strip():
            entity["status"] = "failed"
            entity["result"] = {"error": "Missing or invalid required field 'query'"}
            entity["processedAt"] = now_iso
            return entity

        entity["status"] = "processing"

        external_data = await fetch_external_data(query.strip())

        if "error" in external_data:
            entity["status"] = "failed"
            entity["result"] = {"error": external_data["error"]}
        else:
            entity["status"] = "completed"
            entity["result"] = {
                "query": query,
                "externalSummary": external_data["abstract"],
            }

        entity["processedAt"] = datetime.utcnow().isoformat() + "Z"

    except Exception as e:
        logger.exception(e)
        entity["status"] = "failed"
        entity["result"] = {"error": f"Internal workflow error: {str(e)}"}
        entity["processedAt"] = datetime.utcnow().isoformat() + "Z"

    return entity


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
            workflow=process_entity_job
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