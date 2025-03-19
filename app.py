from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
import uuid
from datetime import datetime
from typing import List

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring  # Schema initialization

from common.config.config import ENTITY_VERSION  # constant for all entity interactions
from app_init.app_init import entity_service, cyoda_token  # external service and token
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# Other workflow functions for different entity_models can be implemented similarly.

# Start-up initialization: ensures that external services are initialized before serving requests.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Data classes for request validation
@dataclass
class IngestRequest:
    source: str

@dataclass
class CrocodileQuery:
    name: str = None
    sex: str = None
    age_min: int = None
    age_max: int = None

# Local job tracking for ingestion tasks.
ENTITY_JOBS = {}  # Stores processing job info keyed by job_id

# Ingestion endpoint.
# This endpoint retrieves external data and for each record, calls entity_service.add_item.
# The workflow function (process_crocodiles) is applied asynchronously before the entity is persisted.
@app.route("/api/crocodiles/ingest", methods=["POST"])
@validate_request(IngestRequest)  # Validator for POST request body.
async def ingest_crocodiles(data: IngestRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    ENTITY_JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}
    logger.info("Starting ingestion job: %s", job_id)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(data.source)
            response.raise_for_status()
            api_data = response.json()
        if not isinstance(api_data, list):
            raise ValueError("Expected list of records from external source")
        # For each record, persist it via the external entity_service.
        # The process_crocodiles workflow function will process each record asynchronously before persistence.
        tasks = [
            entity_service.add_item(
                token=cyoda_token,
                entity_model="crocodiles",
                entity_version=ENTITY_VERSION,  # Always use this constant
                entity=record,
                )
            for record in api_data
        ]
        # Await all tasks concurrently.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Check for exceptions in the results.
        errors = [str(res) for res in results if isinstance(res, Exception)]
        if errors:
            ENTITY_JOBS[job_id]["status"] = "failed"
            logger.error("Ingestion job %s encountered errors: %s", job_id, errors)
            return jsonify({"error": "Failed to ingest some records", "job_id": job_id}), 500
        ENTITY_JOBS[job_id]["status"] = "complete"
        logger.info("Ingestion job %s completed, processed %d records", job_id, len(api_data))
        return jsonify({"message": "Data ingestion completed", "job_id": job_id})
    except Exception as e:
        logger.exception("Ingestion job %s failed: %s", job_id, e)
        ENTITY_JOBS[job_id]["status"] = "failed"
        return jsonify({"error": "Failed to ingest data", "job_id": job_id}), 500

# GET endpoint for retrieving crocodile entities.
# It uses query parameters to optionally filter the returned records.
@app.route("/api/crocodiles", methods=["GET"])
@validate_querystring(CrocodileQuery)  # Validator for query string parameters.
async def get_crocodiles():
    try:
        name = request.args.get("name", type=str)
        sex = request.args.get("sex", type=str)
        age_min = request.args.get("age_min", type=int)
        age_max = request.args.get("age_max", type=int)

        # Build filtering conditions.
        condition = {}
        if name:
            condition["name"] = name
        if sex:
            condition["sex"] = sex
        if age_min is not None:
            condition["age_min"] = age_min
        if age_max is not None:
            condition["age_max"] = age_max

        if condition:
            items = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model="crocodiles",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            items = await entity_service.get_items(
                token=cyoda_token,
                entity_model="crocodiles",
                entity_version=ENTITY_VERSION,
            )
        logger.info("Retrieved %d records", len(items))
        return jsonify(items)
    except Exception as e:
        logger.exception("GET /api/crocodiles failed: %s", e)
        return jsonify({"error": "Failed to retrieve data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)