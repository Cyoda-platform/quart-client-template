from datetime import datetime
import asyncio
import uuid
import aiohttp
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Initialize Quart app and schema
app = Quart(__name__)
QuartSchema(app)

EXTERNAL_API_URL = "https://test-api.k6.io/public/crocodiles/"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dummy dataclass for ingestion endpoint (no payload expected)
@dataclass
class IngestRequest:
    # This is a dummy field to satisfy the validate_request decorator.
    dummy: str = ""

# Dataclass for filter endpoint
@dataclass
class FilterCrocodilesRequest:
    # Using only primitives per instructions.
    name: str = ""
    sex: str = ""
    min_age: int = 0
    max_age: int = 200

# Workflow function to process crocodile entity before persistence.
async def process_crocodiles(entity):
    # Example: add a processed timestamp to the entity.
    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
    # You can add other processing steps here.
    return entity

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)  # Workaround: For POST endpoints, validate_request is added after route declaration.
async def ingest_crocodiles(data: IngestRequest):
    # Retrieve data from the external API using aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(EXTERNAL_API_URL) as resp:
            # TODO: Add error handling for non-200 responses
            external_data = await resp.json()

    # Use external entity_service to add the fetched data.
    # The external service processes the entity asynchronously with process_crocodiles workflow.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="crocodiles",
        entity_version=ENTITY_VERSION,
        entity=external_data,
        workflow=process_crocodiles  # Workflow function applied to the entity before persistence
    )
    # Return only the id; full entity details can be retrieved later.
    return jsonify({
        "status": "success",
        "id": new_id
    })

@app.route('/api/crocodiles/filter', methods=['POST'])
@validate_request(FilterCrocodilesRequest)  # Workaround: For POST endpoints, validate_request is added after route declaration.
async def filter_crocodiles(data: FilterCrocodilesRequest):
    # Build condition dict based on the validated request data.
    # The external service is expected to process these conditions.
    condition = {
        "name": data.name,
        "sex": data.sex,
        "min_age": data.min_age,
        "max_age": data.max_age
    }
    results = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="crocodiles",
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    return jsonify({
        "status": "success",
        "results": results
    })

@app.route('/api/crocodiles/results', methods=['GET'])
async def get_all_crocodiles():
    data = await entity_service.get_items(
        token=cyoda_token,
        entity_model="crocodiles",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({
        "status": "success",
        "data": data
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)