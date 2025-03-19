#!/usr/bin/env python3
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

# Workflow function for the "crocodiles" entity.
# This function takes the entity data as its only argument,
# applies any asynchronous tasks (e.g. fetching supplementary data) and modifies the entity.
async def process_crocodiles(entity: dict) -> dict:
    # Update entity state: add a processing timestamp.
    entity["processed_at"] = datetime.utcnow().isoformat()
    # Example of additional asynchronous work:
    # Fetch supplementary data from a secondary API (for a different entity_model).
    try:
        async with httpx.AsyncClient() as client:
            # This URL is an example; in real usage, provide a valid endpoint.
            response = await client.get("https://example.com/api/supplementary")
            response.raise_for_status()
            supplementary_data = response.json()
        # Add supplementary data to the entity.
        entity["supplementary"] = supplementary_data
    except Exception as e:
        logger.exception("Failed to fetch supplementary data: %s", e)
        # Optionally, you can set a default value or continue.
        entity["supplementary"] = {}
    # You can perform other asynchronous tasks here.
    return entity

# Start-up initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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

# Local job tracking for ingestion
ENTITY_JOBS = {}  # Stores processing job info keyed by job_id

# For POST endpoints, route decorator comes first, then validate_request.
@app.route("/api/crocodiles/ingest", methods=["POST"])
@validate_request(IngestRequest)  # Workaround for POST: validator added after route
async def ingest_crocodiles(data: IngestRequest):
    """
    Ingest crocodile data from the external API and store it into the external entity_service.
    Each record is processed asynchronously by the workflow function before persistence.
    Returns a job ID for tracking the ingestion status.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    ENTITY_JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}
    logger.info("Starting ingestion job: %s", job_id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(data.source)
            response.raise_for_status()
            api_data = response.json()
        # For each record, call add_item with the workflow function.
        tasks = [
            entity_service.add_item(
                token=cyoda_token,
                entity_model="crocodiles",
                entity_version=ENTITY_VERSION,  # always use this constant
                entity=record,
                workflow=process_crocodiles  # Workflow function applied just before persistence
            )
            for record in api_data
        ]
        # Await all tasks concurrently.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Check for errors in results.
        if any(isinstance(res, Exception) for res in results):
            ENTITY_JOBS[job_id]["status"] = "failed"
            logger.error("Ingestion job %s encountered errors", job_id)
            return jsonify({"error": "Failed to ingest some records", "job_id": job_id}), 500
        ENTITY_JOBS[job_id]["status"] = "complete"
        logger.info("Ingestion job %s completed, processed %d records", job_id, len(api_data))
        return jsonify({"message": "Data ingestion completed", "job_id": job_id})
    except Exception as e:
        logger.exception(e)
        ENTITY_JOBS[job_id]["status"] = "failed"
        return jsonify({"error": "Failed to ingest data", "job_id": job_id}), 500

# For GET endpoints, validate_querystring decorator should be placed first.
@validate_querystring(CrocodileQuery)  # Workaround for GET: validator added first
@app.route("/api/crocodiles", methods=["GET"])
async def get_crocodiles():
    """
    Retrieve filtered crocodile data from the external entity_service.
    Filtering parameters:
      - name: Filter by name (case-insensitive substring match)
      - sex: Filter by sex ('M' or 'F')
      - age_min: Minimum age (inclusive)
      - age_max: Maximum age (inclusive)
    """
    try:
        name = request.args.get("name", type=str)
        sex = request.args.get("sex", type=str)
        age_min = request.args.get("age_min", type=int)
        age_max = request.args.get("age_max", type=int)

        # Build filtering condition; if no filter provided, call get_items
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
        logger.info("Returning %d records", len(items))
        return jsonify(items)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)