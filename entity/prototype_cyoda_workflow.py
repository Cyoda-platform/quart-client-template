#!/usr/bin/env python3
import asyncio
import datetime
import uuid
from dataclasses import asdict, dataclass, field

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request
import aiohttp

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Workaround: For GET endpoints with query parameters validation must be first, but here only POST/PUT use validation.

# Local cache for fetched external records remains as is.
fetched_data = {}      # key: datasource technical_id, value: list of fetched external records

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

# Workflow function to be applied to datasource entities before persistence.
# This function encapsulates business logic that was previously inside the controller.
# Any asynchronous tasks and manipulation of the entity can be done here.
async def process_datasource(entity):
    # Add a creation timestamp if not already set.
    if "created_at" not in entity:
        entity["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    # You can add additional processing logic here.
    # For example, setting a unique identifier if needed:
    if "id" not in entity:
        entity["id"] = str(uuid.uuid4())
    # As an example of fire-and-forget secondary task, we can start an async logging task.
    asyncio.create_task(log_entity_creation(entity))
    return entity

# Example asynchronous logging task that could be used as a supplementary process.
async def log_entity_creation(entity):
    # Simulate asynchronous logging (e.g., sending info to an external monitoring service)
    await asyncio.sleep(0.1)
    # In a real scenario, replace this print with an actual logging call.
    print(f"Entity created with id: {entity.get('id')} at {entity.get('created_at')}")

# Startup initialization for external repository
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data Source Management Endpoints

@app.route('/datasources', methods=['POST'])
@validate_request(CreateDatasource)  # For POST, validation decorator goes second
async def create_datasource(data: CreateDatasource):
    # Basic validation check (required fields ensured by dataclass validation)
    if not data.datasource_name or not data.url:
        abort(400, "datasource_name and url are required")
    # Build datasource object using request data.
    datasource = {
        "datasource_name": data.datasource_name,
        "url": data.url,
        "uri_params": data.uri_params,
        "authorization_header": data.authorization_header
    }
    # Call external entity_service to add datasource.
    # The workflow function process_datasource will be invoked asynchronously before persisting the entity.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=datasource,  # the validated data object
        workflow=process_datasource  # Workflow function applied to the entity before persistence.
    )
    return jsonify({"id": new_id}), 201

@app.route('/datasources', methods=['GET'])
async def get_datasources():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(items)

@app.route('/datasources/<technical_id>', methods=['GET'])
async def get_datasource(technical_id):
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=technical_id
    )
    if not datasource:
        abort(404, "Datasource not found")
    return jsonify(datasource)

@app.route('/datasources/<technical_id>', methods=['PUT'])
@validate_request(UpdateDatasource)  # For PUT, validation decorator goes second
async def update_datasource(data: UpdateDatasource, technical_id):
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=technical_id
    )
    if not datasource:
        abort(404, "Datasource not found")
    if data.datasource_name:
        datasource["datasource_name"] = data.datasource_name
    if data.url:
        datasource["url"] = data.url
    if data.uri_params:
        datasource["uri_params"] = data.uri_params
    if data.authorization_header:
        datasource["authorization_header"] = data.authorization_header
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        entity=datasource,
        meta={}
    )
    return jsonify(datasource)

@app.route('/datasources/<technical_id>', methods=['DELETE'])
async def delete_datasource(technical_id):
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=technical_id
    )
    if not datasource:
        abort(404, "Datasource not found")
    await entity_service.delete_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        entity=datasource,
        meta={}
    )
    fetched_data.pop(technical_id, None)
    return '', 204

# External API Data Fetch and Persistence

async def process_fetch(datasource):
    headers = {"Accept": "application/json"}
    if datasource.get("authorization_header"):
        headers["Authorization"] = datasource["authorization_header"]
    
    url = datasource["url"]
    params = datasource.get("uri_params", {})

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception as e:
            return None

    fetched_data.setdefault(datasource.get("technical_id", ""), [])
    if isinstance(data, list):
        fetched_data[datasource.get("technical_id", "")].extend(data)
        return len(data)
    else:
        fetched_data[datasource.get("technical_id", "")].append(data)
        return 1

@app.route('/datasources/<technical_id>/fetch', methods=['POST'])
async def fetch_datasource_data(technical_id):
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=technical_id
    )
    if not datasource:
        abort(404, "Datasource not found")
    datasource["technical_id"] = technical_id
    task = asyncio.create_task(process_fetch(datasource))
    records_count = await task

    if records_count is None:
        abort(500, "Failed to fetch data from external API")

    response = {
        "message": "Data successfully retrieved and persisted.",
        "fetched_records": records_count,
        "datasource_id": technical_id
    }
    return jsonify(response)

@app.route('/datasources/<technical_id>/data', methods=['GET'])
async def get_fetched_data(technical_id):
    if not await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=technical_id
    ):
        abort(404, "Datasource not found")
    data = fetched_data.get(technical_id, [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)