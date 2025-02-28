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

# Background processing function (simulate processing task)
async def process_entity(entity_job, data):
    # TODO: Implement any additional processing if required for each entity
    await asyncio.sleep(1)
    entity_job["status"] = "done"

# Endpoint: Create Datasource
@app.route('/datasources', methods=['POST'])
@validate_request(DatasourceBody)  # For POST endpoints, validate_request comes after @app.route due to known quart-schema issue.
async def create_datasource(data: DatasourceBody):
    # Call external service to add the datasource
    datasource_data = data.__dict__
    generated_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="datasource",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=datasource_data
    )
    return jsonify({
        "message": "Datasource created successfully",
        "datasource_id": generated_id
    }), 201

# Endpoint: Update Datasource
@app.route('/datasources/<datasource_id>', methods=['PUT'])
@validate_request(DatasourceBody)  # Workaround: @app.route comes first for POST/PUT endpoints.
async def update_datasource(data: DatasourceBody, datasource_id):
    # Check for existence
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

# Endpoint: Fetch Data from External API via Datasource using GET (instead of POST)
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

    additional_params = data.__dict__
    # Build headers for external API call; note: GET requests typically do not need "Content-Type"
    headers = {"Accept": "application/json"}
    if datasource.get("authorization_header"):
        headers["Authorization"] = datasource.get("authorization_header")

    # Create a job to track async processing (fire-and-forget)
    job_id = generate_id()
    entity_job = {"status": "processing", "requestedAt": time.time()}

    # Fire and forget the fetch processing task.
    asyncio.create_task(process_fetch(job_id, datasource, additional_params, headers, entity_job))

    return jsonify({
        "message": "Data fetch initiated",
        "job_id": job_id
    })

# Background function to call external API, process, and persist data using GET request
async def process_fetch(job_id, datasource, additional_params, headers, entity_job):
    async with aiohttp.ClientSession() as session:
        # Merge datasource uri_params with additional_params if provided
        params = datasource.get("uri_params", {}).copy()
        params.update(additional_params.get("additional_params", {}))
        
        try:
            async with session.get(datasource.get("url"), params=params, headers=headers) as resp:
                if resp.headers.get('Content-Type', '').startswith("application/json"):
                    json_data = await resp.json()
                else:
                    # TODO: Implement proper handling for non-JSON responses
                    json_data = []
        except Exception as e:
            # TODO: Add proper error logging and handling
            entity_job["status"] = "failed"
            return

    ds_name = datasource.get("datasource_name")
    count = 0
    for record in json_data:
        # Add datasource identifier to the record for later retrieval
        record["datasource_name"] = ds_name
        # Persist each record using external service call
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="persisted_data",
            entity_version=ENTITY_VERSION,
            entity=record
        )
        count += 1

    await process_entity(entity_job, json_data)
    entity_job["fetched_count"] = count
    entity_job["status"] = "completed"

# Endpoint: Retrieve Persisted Data for a Datasource
@app.route('/data/<datasource_name>', methods=['GET'])
async def get_persisted_data(datasource_name):
    data = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="persisted_data",
        entity_version=ENTITY_VERSION,
        condition={"datasource_name": datasource_name}
    )
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)