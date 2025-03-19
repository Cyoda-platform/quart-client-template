#!/usr/bin/env python3
import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION  # always use this constant for entity version
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema

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

# Fetch external data from the provided URL.
async def fetch_crocodile_data(source_url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url)
            response.raise_for_status()  # Raises an exception for HTTP errors
            return response.json()
    except Exception as e:
        logger.exception("Error fetching crocodile data from %s: %s", source_url, e)
        raise

# Workflow function applied to the crocodile entity asynchronously before persistence.
# This function takes the entity (a dict) as its only argument and may modify its state.
async def process_crocodile(entity):
    try:
        # Example: add a timestamp indicating when the entity was processed.
        entity["processed_at"] = datetime.datetime.utcnow().isoformat()
        # Example: perform additional asynchronous tasks if required.
        # For instance, you could retrieve supplementary data from a different entity_model.
        # Make sure to catch exceptions and log them if needed.
        # Do not call add_item/update/delete for the current entity_model to avoid recursion.
        await asyncio.sleep(0)  # Dummy await representing async work.
    except Exception as e:
        logger.exception("Error in workflow processing for entity %s: %s", entity, e)
        # If needed, modify entity state to flag the error.
        entity["workflow_error"] = str(e)
    return entity

# Process a batch of crocodile entities.
# For each entity in the batch, call add_item with the workflow function process_crocodile.
async def process_crocodile_batch(data):
    entity_model = "crocodiles"
    tasks = []
    for item in data:
        # Each add_item will invoke process_crocodile before persistence.
        tasks.append(entity_service.add_item(
            token=cyoda_token,
            entity_model=entity_model,
            entity_version=ENTITY_VERSION,
            entity=item,
            workflow=process_crocodile
        ))
    # Run all add_item tasks concurrently.
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            logger.exception("Error adding entity: %s", res)
        else:
            logger.info("Successfully added crocodile entity with id: %s", res)
    return results

@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        logger.exception("Startup error: %s", e)
        raise

# The ingest endpoint fetches external crocodile data and then defers processing to the workflow functions.
@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)
async def ingest_crocodiles(data: IngestRequest):
    try:
        source = data.source if data.source else "https://test-api.k6.io/public/crocodiles/"
        fetched_data = await fetch_crocodile_data(source)
        job_id = "job-" + str(datetime.datetime.utcnow().timestamp())
        logger.info("Starting ingestion job %s", job_id)
        # Fire and forget: process the batch of entities, each of which will be processed by process_crocodile.
        asyncio.create_task(process_crocodile_batch(fetched_data))
        return jsonify({
            "status": "success",
            "message": "Data ingestion started",
            "job_id": job_id
        })
    except Exception as e:
        logger.exception("Ingestion error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# The endpoint to retrieve crocodile entities with optional filtering.
@validate_querystring(FilterParams)
@app.route('/api/crocodiles/', methods=['GET'])
async def get_crocodiles():
    try:
        entity_model = "crocodiles"
        # Retrieve filter parameters from query strings.
        name_filter = request.args.get("name")
        sex_filter = request.args.get("sex")
        min_age = request.args.get("min_age", type=int)
        max_age = request.args.get("max_age", type=int)

        condition = {}
        if name_filter:
            condition["name"] = name_filter
        if sex_filter:
            condition["sex"] = sex_filter
        if min_age is not None:
            condition["min_age"] = min_age
        if max_age is not None:
            condition["max_age"] = max_age

        if condition:
            results = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model=entity_model,
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            results = await entity_service.get_items(
                token=cyoda_token,
                entity_model=entity_model,
                entity_version=ENTITY_VERSION,
            )
        return jsonify({"status": "success", "data": results})
    except Exception as e:
        logger.exception("Error retrieving crocodile data: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)