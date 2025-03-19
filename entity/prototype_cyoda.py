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

# Remove the local in-memory cache since external service is used

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
    # Instead of writing to a local cache, add each item via the external service
    entity_model = "crocodiles"
    for item in data:
        try:
            # Add each item to the external service.
            # We call add_item; note that the external service will generate an id.
            await entity_service.add_item(
                token=cyoda_token,
                entity_model=entity_model,
                entity_version=ENTITY_VERSION,
                entity=item
            )
            logger.info("Added crocodile item to external service.")
        except Exception as e:
            logger.exception(e)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# For POST requests, the validation decorator is added after @app.route,
# and for GET requests, the validation decorator is added before @app.route (workaround for a known issue in quart-schema)

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)  # For POST, validation comes after route decorator
async def ingest_crocodiles(data: IngestRequest):
    try:
        source = data.source if data.source else "https://test-api.k6.io/public/crocodiles/"
        fetched_data = await fetch_crocodile_data(source)
        requested_at = datetime.datetime.utcnow().isoformat()
        # Create a job_id
        job_id = "job-" + str(datetime.datetime.utcnow().timestamp())
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
        entity_model = "crocodiles"
        # Retrieve filter parameters from query strings using standard approach
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
            # Use condition-based retrieval from the external service
            results = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model=entity_model,
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            # Retrieve all items if no condition is specified.
            results = await entity_service.get_items(
                token=cyoda_token,
                entity_model=entity_model,
                entity_version=ENTITY_VERSION,
            )

        return jsonify({"status": "success", "data": results})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)