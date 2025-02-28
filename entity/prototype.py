import asyncio
import time
import uuid
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory storage for datasources and persisted external API data
datasources = {}        # Key: datasource_id, Value: datasource details dictionary
persisted_data = {}     # Key: datasource_name, Value: list of records from external API

# Utility function to generate unique IDs
def generate_id():
    return str(uuid.uuid4())

# Background processing function (simulate processing task)
async def process_entity(entity_job, data):
    # TODO: Implement any additional processing if required for each entity
    await asyncio.sleep(1)
    entity_job["status"] = "done"

# Endpoint: Create Datasource
@app.route('/datasources', methods=['POST'])
async def create_datasource():
    body = await request.get_json()
    if not body:
        abort(400, description="Invalid JSON body")
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
async def update_datasource(datasource_id):
    if datasource_id not in datasources:
        abort(404, description="Datasource not found")
    body = await request.get_json()
    if not body:
        abort(400, description="Invalid JSON body")
    datasources[datasource_id].update(body)
    return jsonify({"message": "Datasource updated successfully"})

# Endpoint: Get All Datasources
@app.route('/datasources', methods=['GET'])
async def get_datasources():
    # Return all datasource objects
    return jsonify(list(datasources.values()))

# Endpoint: Fetch Data from External API via Datasource
@app.route('/datasources/<datasource_name>/fetch', methods=['POST'])
async def fetch_data(datasource_name):
    # Look up datasource by datasource_name (not by id)
    datasource = None
    for ds in datasources.values():
        if ds.get("datasource_name") == datasource_name:
            datasource = ds
            break

    if not datasource:
        abort(404, description="Datasource not found for given name")

    # Retrieve request data (additional parameters)
    additional_params = await request.get_json() or {}
    # Build headers for the external API call
    headers = {"Content-Type": "application/json"}
    if datasource.get("authorization_header"):
        headers["Authorization"] = datasource.get("authorization_header")

    # Create a job to track async processing (fire-and-forget)
    job_id = generate_id()
    entity_job = {"status": "processing", "requestedAt": time.time()}

    # Fire and forget the processing task
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

# Endpoint: Retrieve Persisted Data for a Datasource
@app.route('/data/<datasource_name>', methods=['GET'])
async def get_persisted_data(datasource_name):
    data = persisted_data.get(datasource_name, [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)