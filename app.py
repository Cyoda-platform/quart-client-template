from common.grpc_client.grpc_client import grpc_stream
import asyncio
import time
import uuid
from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request  # For POST/PUT endpoints, route decorator comes first then validate_request
import aiohttp

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Utility function to generate unique IDs (used for job tracking)
def generate_id():
    return str(uuid.uuid4())

# Dataclasses for request validation
@dataclass
class DatasourceBody:
    datasource_name: str
    url: str
    uri_params: dict  # Optionally add deeper validations if needed
    authorization_header: str

@dataclass
class FetchParams:
    additional_params: dict

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Endpoint: Create Datasource
@app.route('/datasources', methods=['POST'])
@validate_request(DatasourceBody)  # Validate after route decorator because of quart-schema known issue.
async def create_datasource(data: DatasourceBody):
    datasource_data = data.__dict__
    try:
        generated_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,  # Always use this constant.
            entity=datasource_data,         # Validated data object.
            )
    except Exception as e:
        abort(500, description=f"Error creating datasource: {e}")
    return jsonify({
        "message": "Datasource created successfully",
        "datasource_id": generated_id
    }), 201

# Endpoint: Update Datasource
@app.route('/datasources/<datasource_id>', methods=['PUT'])
@validate_request(DatasourceBody)
async def update_datasource(data: DatasourceBody, datasource_id):
    existing = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=datasource_id
    )
    if not existing:
        abort(404, description="Datasource not found")
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            meta={}
        )
    except Exception as e:
        abort(500, description=f"Error updating datasource: {e}")
    return jsonify({"message": "Datasource updated successfully"})

# Endpoint: Get All Datasources
@app.route('/datasources', methods=['GET'])
async def get_datasources():
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="datasource",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        abort(500, description=f"Error retrieving datasources: {e}")
    return jsonify(items)

# Endpoint: Fetch Data from external API via Datasource using POST.
@app.route('/datasources/<datasource_name>/fetch', methods=['POST'])
@validate_request(FetchParams)
async def fetch_data(data: FetchParams, datasource_name):
    # Retrieve datasource entity based on the given name.
    # ds_list = await entity_service.get_items_by_condition(
    #     token=cyoda_token,
    #     entity_model="datasource",
    #     entity_version=ENTITY_VERSION,
    #     condition={"datasource_name": datasource_name}
    # )
    ds_list = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=datasource_name
    )
    if not ds_list or len(ds_list) == 0:
        abort(404, description="Datasource not found for given name")
    datasource = ds_list
    # datasource = ds_list[0]

    # Build a fetch_job entity that drives the external API call.
    fetch_job_entity = {
        "datasource_name": datasource_name,
        "url": datasource.get("url"),
        "uri_params": datasource.get("uri_params", {}),
        "authorization_header": datasource.get("authorization_header"),
        "additional_params": data.__dict__.get("additional_params", {}),
        "status": "processing",
        "requested_at": time.time()
    }
    
    try:
        # Persist the fetch_job with its workflow.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="fetch_job",
            entity_version=ENTITY_VERSION,
            entity=fetch_job_entity,
            )
    except Exception as e:
        abort(500, description=f"Error initiating data fetch: {e}")

    return jsonify({
        "message": "Data fetch initiated",
        "job_id": job_id
    })

# Endpoint: Retrieve Persisted Data for a Datasource
@app.route('/data/<datasource_name>', methods=['GET'])
async def get_persisted_data(datasource_name):
    try:
        # data_items = await entity_service.get_items_by_condition(
        #     token=cyoda_token,
        #     entity_model="persisted_data",
        #     entity_version=ENTITY_VERSION,
        #     condition={"datasource_name": datasource_name}
        # )
        data_items = await entity_service.get_items(
            token=cyoda_token,
            # entity_model="persisted_data",
            entity_model=datasource_name,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        abort(500, description=f"Error retrieving persisted data: {e}")
    return jsonify(data_items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)