from common.grpc_client.grpc_client import grpc_stream
import asyncio
import datetime
import uuid
import logging
from dataclasses import dataclass, field

from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request
import aiohttp

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)  # Required for endpoints using validation

# Local cache for fetched external records (key: datasource technical_id, value: list of records)
fetched_data = {}

# Dataclasses for request validation
@dataclass
class CreateDatasource:
    datasource_name: str
    url: str
    uri_params: dict = field(default_factory=dict)
    authorization_header: str = ""

@dataclass
class UpdateDatasource:
    datasource_name: str = ""
    url: str = ""
    uri_params: dict = field(default_factory=dict)
    authorization_header: str = ""

# Additional workflow functions can be implemented here for other entity models if needed.

# Startup initialization: run any required external initializations.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
        logger.info("Cyoda initialization complete.")
    except Exception as e:
        logger.exception("Error during startup initialization: %s", e)
        raise e

# Endpoint: Create Datasource
@app.route('/datasources', methods=['POST'])
@validate_request(CreateDatasource)
async def create_datasource(data: CreateDatasource):
    # Basic validation (dataclass already ensures required fields structure)
    if not data.datasource_name or not data.url:
        abort(400, "datasource_name and url are required")
    # Build the datasource object.
    datasource = {
        "datasource_name": data.datasource_name,
        "url": data.url,
        "uri_params": data.uri_params,
        "authorization_header": data.authorization_header,
    }
    try:
        # Persist datasource using entity_service.
        # The workflow function process_datasource will be executed before persisting.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,  # Always use this constant
            entity=datasource,
            )
    except Exception as e:
        logger.exception("Error creating datasource: %s", e)
        abort(500, "Failed to create datasource")
    return jsonify({"id": new_id}), 201

# Endpoint: Get all Datasources
@app.route('/datasources', methods=['GET'])
async def get_datasources():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Error retrieving datasources: %s", e)
        abort(500, "Failed to retrieve datasources")
    return jsonify(items)

# Endpoint: Get single Datasource by technical_id
@app.route('/datasources/<technical_id>', methods=['GET'])
async def get_datasource(technical_id):
    try:
        datasource = await entity_service.get_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id
        )
    except Exception as e:
        logger.exception("Error retrieving datasource: %s", e)
        abort(500, "Error retrieving datasource")
    if not datasource:
        abort(404, "Datasource not found")
    return jsonify(datasource)

# Endpoint: Update Datasource
@app.route('/datasources/<technical_id>', methods=['PUT'])
@validate_request(UpdateDatasource)
async def update_datasource(data: UpdateDatasource, technical_id):
    try:
        datasource = await entity_service.get_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id
        )
    except Exception as e:
        logger.exception("Error retrieving datasource for update: %s", e)
        abort(500, "Error retrieving datasource")
    if not datasource:
        abort(404, "Datasource not found")
    # Update mutable fields if provided.
    if data.datasource_name:
        datasource["datasource_name"] = data.datasource_name
    if data.url:
        datasource["url"] = data.url
    if data.uri_params:
        datasource["uri_params"] = data.uri_params
    if data.authorization_header:
        datasource["authorization_header"] = data.authorization_header
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            entity=datasource,
            meta={}
        )
    except Exception as e:
        logger.exception("Error updating datasource: %s", e)
        abort(500, "Failed to update datasource")
    return jsonify(datasource)

# Endpoint: Delete Datasource
@app.route('/datasources/<technical_id>', methods=['DELETE'])
async def delete_datasource(technical_id):
    try:
        datasource = await entity_service.get_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id
        )
    except Exception as e:
        logger.exception("Error retrieving datasource for deletion: %s", e)
        abort(500, "Error retrieving datasource")
    if not datasource:
        abort(404, "Datasource not found")
    try:
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            entity=datasource,
            meta={}
        )
    except Exception as e:
        logger.exception("Error deleting datasource: %s", e)
        abort(500, "Failed to delete datasource")
    # Clean up local in-memory cache if present.
    fetched_data.pop(technical_id, None)
    return '', 204

# Function to fetch external API data for a datasource.
async def process_fetch(datasource):
    headers = {"Accept": "application/json"}
    if datasource.get("authorization_header"):
        headers["Authorization"] = datasource["authorization_header"]
    url = datasource.get("url")
    params = datasource.get("uri_params", {})
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.error("Failed to fetch data; HTTP status: %s", resp.status)
                    return None
                data = await resp.json()
    except Exception as e:
        logger.exception("Exception during external API fetch: %s", e)
        return None

    # Use datasource technical_id for caching fetched data.
    tech_id = datasource.get("technical_id", "")
    if not tech_id:
        logger.error("Datasource technical_id missing in fetched entity")
        return None

    fetched_data.setdefault(tech_id, [])
    if isinstance(data, list):
        fetched_data[tech_id].extend(data)
        return len(data)
    else:
        fetched_data[tech_id].append(data)
        return 1

# Endpoint: Trigger external data fetch for a datasource.
@app.route('/datasources/<technical_id>/fetch', methods=['POST'])
async def fetch_datasource_data(technical_id):
    try:
        datasource = await entity_service.get_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id
        )
    except Exception as e:
        logger.exception("Error retrieving datasource for fetch: %s", e)
        abort(500, "Error retrieving datasource")
    if not datasource:
        abort(404, "Datasource not found")
    # Ensure technical_id is available in the datasource for caching purpose.
    datasource["technical_id"] = technical_id
    records_count = await process_fetch(datasource)
    if records_count is None:
        abort(500, "Failed to fetch data from external API")
    response = {
        "message": "Data successfully retrieved and persisted.",
        "fetched_records": records_count,
        "datasource_id": technical_id
    }
    return jsonify(response)

# Endpoint: Retrieve fetched data from local in-memory cache.
@app.route('/datasources/<technical_id>/data', methods=['GET'])
async def get_fetched_data(technical_id):
    try:
        exists = await entity_service.get_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id
        )
    except Exception as e:
        logger.exception("Error checking existence of datasource: %s", e)
        abort(500, "Error retrieving datasource")
    if not exists:
        abort(404, "Datasource not found")
    data = fetched_data.get(technical_id, [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)