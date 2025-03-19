import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

# In-memory persistence (acting as our local cache/database)
DATABASE = []

# Data models for request validation

@dataclass
class IngestRequest:
    source: str

@dataclass
class FilterParams:
    name: Optional[str] = None
    sex: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None

async def fetch_crocodile_data(source_url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(source_url)
        response.raise_for_status()  # Raises an exception for HTTP errors
        data = response.json()
        return data

async def process_crocodiles(data):
    # TODO: Add any additional processing logic if required.
    global DATABASE
    # For the prototype, we simply assign the data to our in-memory store.
    DATABASE = data
    logger.info("Crocodile data ingested into the local cache.")
    return

# NOTE: For POST requests, validation decorator is added after @app.route,
# and for GET requests, validation decorator is added before @app.route (workaround for a known issue in quart-schema)

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)  # For POST, validation comes after route decorator
async def ingest_crocodiles(data: IngestRequest):
    try:
        source = data.source if data.source else "https://test-api.k6.io/public/crocodiles/"
        fetched_data = await fetch_crocodile_data(source)
        requested_at = datetime.datetime.utcnow().isoformat()
        job_id = "job-" + str(datetime.datetime.utcnow().timestamp())
        entity_job = {job_id: {"status": "processing", "requestedAt": requested_at}}
        logger.info("Starting ingestion job %s", job_id)
        # Fire and forget the processing task.
        asyncio.create_task(process_crocodiles(fetched_data))
        return jsonify({
            "status": "success",
            "message": "Data ingestion started",
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@validate_querystring(FilterParams)  # For GET, validation comes first (workaround for a quart-schema issue)
@app.route('/api/crocodiles/', methods=['GET'])
async def get_crocodiles():
    try:
        # Retrieve filter parameters from query strings using standard approach
        name_filter = request.args.get("name")
        sex_filter = request.args.get("sex")
        min_age = request.args.get("min_age", type=int)
        max_age = request.args.get("max_age", type=int)

        results = DATABASE

        if name_filter:
            results = [c for c in results if c.get("name") == name_filter]
        if sex_filter:
            results = [c for c in results if c.get("sex") == sex_filter]
        if min_age is not None:
            results = [c for c in results if c.get("age", 0) >= min_age]
        if max_age is not None:
            results = [c for c in results if c.get("age", 0) <= max_age]

        return jsonify({"status": "success", "data": results})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)