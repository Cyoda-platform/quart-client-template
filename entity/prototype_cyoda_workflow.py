import asyncio
import time
import uuid
from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request  # Workaround: For POST/PUT endpoints, route decorator comes first, then validate_request.
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
    uri_params: dict  # TODO: Consider validating the structure of uri_params further if required.
    authorization_header: str

@dataclass
class FetchParams:
    additional_params: dict

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Workflow function for datasource entity; applied before persistence
async def process_datasource(entity):
    # Example: Add a timestamp indicating when the datasource was processed
    entity["processed_at"] = time.time()
    return entity

# Workflow function for persisted_data entity; applied before persistence
async def process_persisted_data(entity):
    # Example: Mark the record as validated
    entity["validated"] = True
    return entity

# Workflow function for fetch_job entity; applied before persistence
# This function will perform the async external API call, create secondary persisted_data entities,
# and update the fetch_job entity state accordingly.
async def process_fetch_job(entity):
    # Build headers from entity; remove header if not needed
    headers = {"Accept": "application/json"}
    auth = entity.get("authorization_header")
    if auth:
        headers["Authorization"] = auth

    # Merge uri_params from datasource and additional_params from request
    uri_params = entity.get("uri_params", {}).copy()
    additional = entity.get("additional_params", {})
    uri_params.update(additional)

    # External API call using the URL from the entity
    url = entity.get("url")
    count = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=uri_params, headers=headers) as resp:
                if resp.headers.get('Content-Type', '').startswith("application/json"):
                    json_data = await resp.json()
                else:
                    # Fallback: if non-JSON, assume empty result set
                    json_data = []
    except Exception as e:
        # If external API call fails, update entity status accordingly
        entity["status"] = "failed"
        entity["error"] = str(e)
        return entity

    # For each record fetched, add datasource identifier and persist as a secondary entity
    datasource_name = entity.get("datasource_name")
    for record in json_data:
        record["datasource_name"] = datasource_name
        # Persist each record using external service call with its own workflow function
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="persisted_data",
            entity_version=ENTITY_VERSION,
            entity=record,
            workflow=process_persisted_data  # Workflow applied for persisted_data
        )
        count += 1

    # Update current fetch_job entity state
    entity["fetched_count"] = count
    entity["status"] = "completed"
    entity["completed_at"] = time.time()
    return entity

# Background processing function (simulate additional processing task)
async def process_entity(entity_job, data):
    await asyncio.sleep(1)
    entity_job["status"] = "done"

# Endpoint: Create Datasource
@app.route('/datasources', methods=['POST'])
@validate_request(DatasourceBody)  # For POST endpoints, validate_request comes after @app.route due to known quart-schema issue.
async def create_datasource(data: DatasourceBody):
    datasource_data = data.__dict__
    generated_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=datasource_data,  # the validated data object
        workflow=process_datasource  # Workflow function applied to the datasource entity
    )
    return jsonify({
        "message": "Datasource created successfully",
        "datasource_id": generated_id
    }), 201

# Endpoint: Update Datasource
@app.route('/datasources/<datasource_id>', methods=['PUT'])
@validate_request(DatasourceBody)  # Workaround: @app.route comes first for POST/PUT endpoints.
async def update_datasource(data: DatasourceBody, datasource_id):
    existing = await entity_service.get_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        technical_id=datasource_id
    )
    if not existing:
        abort(404, description="Datasource not found")
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=data.__dict__,
        meta={}
    )
    return jsonify({"message": "Datasource updated successfully"})

# Endpoint: Get All Datasources
@app.route('/datasources', methods=['GET'])
async def get_datasources():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(items)

# Endpoint: Fetch Data from External API via Datasource using POST
@app.route('/datasources/<datasource_name>/fetch', methods=['POST'])
@validate_request(FetchParams)  # Workaround: @app.route comes first for POST endpoints.
async def fetch_data(data: FetchParams, datasource_name):
    # Retrieve datasource by condition using external service call
    ds_list = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,
        condition={"datasource_name": datasource_name}
    )
    if not ds_list or len(ds_list) == 0:
        abort(404, description="Datasource not found for given name")
    datasource = ds_list[0]

    # Build a fetch_job entity that will drive the external API call asynchronously
    fetch_job_entity = {
        "datasource_name": datasource_name,
        "url": datasource.get("url"),
        "uri_params": datasource.get("uri_params", {}),
        "authorization_header": datasource.get("authorization_header"),
        "additional_params": data.__dict__.get("additional_params", {}),
        "status": "processing",
        "requested_at": time.time()
    }

    # Persist the fetch job with its workflow; workflow function will execute the external fetch,
    # create secondary persisted_data entities, and update the fetch_job state.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="fetch_job",
        entity_version=ENTITY_VERSION,
        entity=fetch_job_entity,
        workflow=process_fetch_job  # Workflow function handles the external API call and related tasks
    )

    return jsonify({
        "message": "Data fetch initiated",
        "job_id": job_id
    })

# Endpoint: Retrieve Persisted Data for a Datasource
@app.route('/data/<datasource_name>', methods=['GET'])
async def get_persisted_data(datasource_name):
    data_items = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="persisted_data",
        entity_version=ENTITY_VERSION,
        condition={"datasource_name": datasource_name}
    )
    return jsonify(data_items)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)