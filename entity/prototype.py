from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import asyncio
import httpx
import logging
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for process jobs (mock persistence)
entity_job: Dict[str, Dict] = {}


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


async def process_entity(job_store: dict, job_id: str, input_data: dict):
    """
    Simulate business logic:
    - Fetch external data based on input query
    - Store results in the job_store with status update
    """
    try:
        query = input_data.get("query")
        if not query:
            raise ValueError("Missing required field 'query' in inputData")

        logger.info(f"Processing job {job_id} with query: {query}")

        external_data = await fetch_external_data(query)

        if "error" in external_data:
            job_store[job_id]["status"] = "failed"
            job_store[job_id]["result"] = {"error": external_data["error"]}
        else:
            result = {
                "query": query,
                "externalSummary": external_data["abstract"],
                "processedAt": datetime.utcnow().isoformat() + "Z",
            }
            job_store[job_id]["status"] = "completed"
            job_store[job_id]["result"] = result

        logger.info(f"Job {job_id} completed with status {job_store[job_id]['status']}")

    except Exception as e:
        logger.exception(e)
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["result"] = {"error": str(e)}


@app.route("/process-data", methods=["POST"])
@validate_request(InputData)  # Validation last for POST requests (issue workaround)
async def post_process_data(data: InputData):
    input_data = {"query": data.query}

    process_id = f"job_{int(datetime.utcnow().timestamp() * 1000)}"
    requested_at = datetime.utcnow().isoformat() + "Z"

    entity_job[process_id] = {"status": "processing", "requestedAt": requested_at}

    asyncio.create_task(process_entity(entity_job, process_id, input_data))

    return jsonify({"processId": process_id, "status": "processing"}), 202


@app.route("/results/<process_id>", methods=["GET"])
# Validation first for GET requests (issue workaround)
async def get_results(process_id):
    job = entity_job.get(process_id)
    if not job:
        return jsonify({"error": f"No job found with processId '{process_id}'"}), 404

    response = {
        "processId": process_id,
        "status": job["status"],
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
