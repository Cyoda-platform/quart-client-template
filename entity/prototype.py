import asyncio
import time
import uuid
from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request  # Workaround: For POST/PUT endpoints, route decorator comes first, then validate_request.
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory storage for datasources and persisted external API data
datasources = {}        # Key: datasource_id, Value: datasource details dictionary
persisted_data = {}     # Key: datasource_name, Value: list of records from external API

# Utility function to generate unique IDs
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

# Background processing function (simulate processing task)
async def process_entity(entity_job, data):
    # TODO: Implement any additional processing if required for each entity
    await asyncio.sleep(1)
    entity_job["status"] = "done"

# Endpoint: Create Datasource
@app.route('/datasources', methods=['POST'])
@validate_request(DatasourceBody)  # For POST endpoints, place validate_request after @app.route due to known quart-schema issue.
async def create_datasource(data: DatasourceBody):
    body = data.__dict__
    datasource_id = generate_id()
    body["id"] = datasource_id
    datasources[datasource_id] = body
    # TODO: Handle duplicate datasource_name if necessary
    return jsonify({
        "message": "Datasource created successfully",
        "datasource_id": datasource_id
    }), 201

# Endpoint: Update Datasource
@app.route('/datasources/<datasource_id>', methods=['PUT'])
@validate_request(DatasourceBody)  # Workaround: @app.route comes first for POST/PUT endpoints.
async def update_datasource(data: DatasourceBody, datasource_id):
    if datasource_id not in datasources:
        abort(404, description="Datasource not found")
    datasources[datasource_id].update(data.__dict__)
    return jsonify({"message": "Datasource updated successfully"})

# Endpoint: Get All Datasources (no validation needed)
@app.route('/datasources', methods=['GET'])
async def get_datasources():
    # Return all datasource objects
    return jsonify(list(datasources.values()))

# Endpoint: Fetch Data from External API via Datasource
@app.route('/datasources/<datasource_name>/fetch', methods=['POST'])
@validate_request(FetchParams)  # Workaround: @app.route comes first for POST endpoints.
async def fetch_data(data: FetchParams, datasource_name):
    # Look up datasource by datasource_name (not by id)
    datasource = None
    for ds in datasources.values():
        if ds.get("datasource_name") == datasource_name:
            datasource = ds
            break

    if not datasource:
        abort(404, description="Datasource not found for given name")

    additional_params = data.__dict__
    # Build headers for the external API call
    headers = {"Content-Type": "application/json"}
    if datasource.get("authorization_header"):
        headers["Authorization"] = datasource.get("authorization_header")

    # Create a job to track async processing (fire-and-forget)
    job_id = generate_id()
    entity_job = {"status": "processing", "requestedAt": time.time()}

    # Fire and forget the processing task.
    asyncio.create_task(process_fetch(job_id, datasource, additional_params, headers, entity_job))

    # Immediate response to user
    return jsonify({
        "message": "Data fetch initiated",
        "job_id": job_id
    })

# Background function to call external API, process, and persist data
async def process_fetch(job_id, datasource, additional_params, headers, entity_job):
    async with aiohttp.ClientSession() as session:
        # Merge datasource uri_params with additional_params if provided
        params = datasource.get("uri_params", {}).copy()
        # TODO: Clarify and adjust parameter merging logic if necessary
        params.update(additional_params.get("additional_params", {}))
        
        try:
            async with session.post(datasource.get("url"), json=params, headers=headers) as resp:
                # Ensure the response is in JSON format as per requirement
                if resp.headers.get('Content-Type', '').startswith("application/json"):
                    json_data = await resp.json()
                else:
                    # TODO: Implement proper handling for non-JSON responses
                    json_data = []
        except Exception as e:
            # TODO: Add proper error logging and handling
            entity_job["status"] = "failed"
            return

    # Persist each record fetched into the in-memory storage under the datasource_name key
    ds_name = datasource.get("datasource_name")
    if ds_name not in persisted_data:
        persisted_data[ds_name] = []

    count = 0
    for record in json_data:
        persisted_data[ds_name].append(record)
        count += 1

    # Simulate any additional processing needed for the fetched data
    await process_entity(entity_job, json_data)
    entity_job["fetched_count"] = count
    entity_job["status"] = "completed"

# Endpoint: Retrieve Persisted Data for a Datasource (no validation needed)
@app.route('/data/<datasource_name>', methods=['GET'])
async def get_persisted_data(datasource_name):
    data = persisted_data.get(datasource_name, [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)