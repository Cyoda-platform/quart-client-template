from common.grpc_client.grpc_client import grpc_stream
import asyncio
import datetime
from uuid import uuid4
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # validate_querystring available if needed

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Startup initialization of external services.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Dataclass for Datasource input validation.
@dataclass
class DatasourceInput:
    datasource_name: str
    url: str
    uri_params: dict = None  # TODO: Consider stricter type definition if required.
    Authorization_Header: str = None

# In-memory job processing simulation (local cache).
entity_jobs = {}

# Endpoint: Create a datasource.
@app.route("/datasources", methods=["POST"])
@validate_request(DatasourceInput)  # POST validation as per Quart-Schema guidelines.
async def create_datasource(data: DatasourceInput):
    # Build the datasource object.
    datasource = {
        "datasource_name": data.datasource_name,
        "url": data.url,
        "uri_params": data.uri_params or {},
        "Authorization_Header": data.Authorization_Header,
        "created_at": current_timestamp()
    }
    # Persist the datasource after applying workflow processing.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,  # always use this constant.
        entity=datasource,
        )
    return jsonify({"id": new_id}), 201

# Endpoint: List all datasources.
@app.route("/datasources", methods=["GET"])
async def list_datasources():
    datasources = await entity_service.get_items(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(datasources)

# Endpoint: Get a single datasource by id.
@app.route("/datasources/<int:ds_id>", methods=["GET"])
async def get_datasource(ds_id):
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=ds_id
    )
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404
    return jsonify(datasource)

# Endpoint: Update a datasource.
@app.route("/datasources/<int:ds_id>", methods=["PUT"])
@validate_request(DatasourceInput)  # PUT validation as per Quart-Schema guidelines.
async def update_datasource(data: DatasourceInput, ds_id):
    # Retrieve the existing datasource.
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=ds_id
    )
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404
    # Update fields from validated data.
    datasource["datasource_name"] = data.datasource_name or datasource.get("datasource_name")
    datasource["url"] = data.url or datasource.get("url")
    datasource["uri_params"] = data.uri_params or datasource.get("uri_params", {})
    datasource["Authorization_Header"] = data.Authorization_Header or datasource.get("Authorization_Header")
    # Persist the updated datasource.
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        entity=datasource,
        meta={}
    )
    return jsonify(datasource)

# Endpoint: Delete a datasource and its related fetched data.
@app.route("/datasources/<int:ds_id>", methods=["DELETE"])
async def delete_datasource(ds_id):
    # Retrieve the datasource.
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=ds_id
    )
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404
    # Delete the datasource.
    await entity_service.delete_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        entity=datasource,
        meta={}
    )
    # Cascade deletion: remove related fetched data.
    fetched_data_list = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="fetched_data",
        entity_version=ENTITY_VERSION,
        condition={"datasource_id": ds_id}
    )
    for record in fetched_data_list:
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="fetched_data",
            entity_version=ENTITY_VERSION,
            entity=record,
            meta={}
        )
    return jsonify({"message": "Datasource deleted successfully"})

# Endpoint: Fetch external data for a datasource.
@app.route("/datasources/<int:ds_id>/fetch", methods=["POST"])
async def fetch_external_data(ds_id):
    # Retrieve the datasource.
    datasource = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=ds_id
    )
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404
    # Create a job record for processing simulation.
    job_id = str(uuid4())
    entity_jobs[job_id] = {"status": "processing", "requestedAt": current_timestamp()}
    # Fetch external data using aiohttp.ClientSession.
    async with aiohttp.ClientSession() as session:
        headers = {"Accept": "application/json"}
        if datasource.get("Authorization_Header"):
            headers["Authorization"] = datasource["Authorization_Header"]
        params = datasource.get("uri_params", {})
        try:
            async with session.get(datasource["url"], headers=headers, params=params) as response:
                external_response = await response.json()
        except Exception as e:
            return jsonify({"error": f"External API request failed: {e}"}), 500
    fetched_ids = []
    # Process and store each fetched data object individually.
    for record in external_response:
        fetched_record = {
            "datasource_id": ds_id,
            "data": record,
            "fetched_at": current_timestamp()
        }
        # Persist fetched data after applying workflow processing.
        fetched_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="fetched_data",
            entity_version=ENTITY_VERSION,
            entity=fetched_record,
            )
        fetched_ids.append(fetched_id)
    # Mark job as completed.
    entity_jobs[job_id]["status"] = "completed"
    result = {
        "datasource_id": ds_id,
        "records_fetched": len(fetched_ids),
        "fetched_data_ids": fetched_ids,
        "message": "Data fetched and persisted successfully"
    }
    return jsonify(result)

# Endpoint: Get fetched data for a datasource.
@app.route("/datasources/<int:ds_id>/fetched_data", methods=["GET"])
async def get_fetched_data(ds_id):
    records = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="fetched_data",
        entity_version=ENTITY_VERSION,
        condition={"datasource_id": ds_id}
    )
    return jsonify(records)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)