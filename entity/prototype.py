import asyncio
import datetime
from uuid import uuid4
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # validate_querystring available if needed

app = Quart(__name__)
QuartSchema(app)

# Dataclass for Datasource input validation
@dataclass
class DatasourceInput:
    datasource_name: str
    url: str
    uri_params: dict = None  # TODO: Consider stricter type definition if required.
    Authorization_Header: str = None

# In-memory persistence mocks
datasources = {}        # {datasource_id: datasource_data}
fetched_data_store = {} # {fetched_data_id: fetched_data_object}
entity_jobs = {}        # Local cache for job processing simulation

# Simple counters for IDs (note: in production, use more robust ID generation)
datasource_counter = 1
fetched_data_counter = 1

# Utility to get current UTC timestamp in ISO format
def current_timestamp():
    return datetime.datetime.utcnow().isoformat() + "Z"

@app.route("/datasources", methods=["POST"])
@validate_request(DatasourceInput)  # Workaround: POST validation added after route decorator as per Quart-Schema guidelines.
async def create_datasource(data: DatasourceInput):
    global datasource_counter
    ds_id = datasource_counter
    datasource_counter += 1

    datasource = {
        "datasource_id": ds_id,
        "datasource_name": data.datasource_name,
        "url": data.url,
        "uri_params": data.uri_params or {},
        "Authorization_Header": data.Authorization_Header,
        "created_at": current_timestamp()
    }
    datasources[ds_id] = datasource
    return jsonify(datasource), 201

@app.route("/datasources", methods=["GET"])
async def list_datasources():
    return jsonify(list(datasources.values()))

@app.route("/datasources/<int:ds_id>", methods=["GET"])
async def get_datasource(ds_id):
    datasource = datasources.get(ds_id)
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404
    return jsonify(datasource)

@app.route("/datasources/<int:ds_id>", methods=["PUT"])
@validate_request(DatasourceInput)  # Workaround: PUT validation added after route decorator as per Quart-Schema guidelines.
async def update_datasource(data: DatasourceInput, ds_id):
    datasource = datasources.get(ds_id)
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404
    # Update only provided fields from validated data
    datasource["datasource_name"] = data.datasource_name or datasource["datasource_name"]
    datasource["url"] = data.url or datasource["url"]
    datasource["uri_params"] = data.uri_params or datasource["uri_params"]
    datasource["Authorization_Header"] = data.Authorization_Header or datasource["Authorization_Header"]
    # TODO: Add more validations if needed.
    datasources[ds_id] = datasource
    return jsonify(datasource)

@app.route("/datasources/<int:ds_id>", methods=["DELETE"])
async def delete_datasource(ds_id):
    if ds_id not in datasources:
        return jsonify({"error": "Datasource not found"}), 404
    # Remove datasource and related fetched data
    del datasources[ds_id]
    # TODO: Consider cascading deletion or mark fetched_data as orphaned if required.
    fetched_data_store_keys = [k for k, v in fetched_data_store.items() if v["datasource_id"] == ds_id]
    for key in fetched_data_store_keys:
        del fetched_data_store[key]
    return jsonify({"message": "Datasource deleted successfully"})

async def process_entity(job_id, data_obj):
    # TODO: Implement actual processing if needed. For now, we just simulate processing delay.
    await asyncio.sleep(0.1)
    entity_jobs[job_id]["status"] = "completed"
    # In a real application, update the processing outcome based on data_obj.
    return

@app.route("/datasources/<int:ds_id>/fetch", methods=["POST"])
async def fetch_external_data(ds_id):
    datasource = datasources.get(ds_id)
    if datasource is None:
        return jsonify({"error": "Datasource not found"}), 404

    # Create a job record for processing simulation
    job_id = str(uuid4())
    entity_jobs[job_id] = {"status": "processing", "requestedAt": current_timestamp()}

    # Fetch external data using aiohttp.ClientSession
    async with aiohttp.ClientSession() as session:
        headers = {"Accept": "application/json"}
        if datasource.get("Authorization_Header"):
            headers["Authorization"] = datasource["Authorization_Header"]
        # TODO: Add other headers or auth mechanisms if required.

        # Build query params from uri_params
        params = datasource.get("uri_params", {})
        try:
            async with session.get(datasource["url"], headers=headers, params=params) as response:
                # TODO: Add more sophisticated error handling for non-200 statuses.
                external_response = await response.json()
        except Exception as e:
            return jsonify({"error": f"External API request failed: {e}"}), 500

    # Process and store each fetched data object individually
    global fetched_data_counter
    fetched_ids = []
    # Assuming external_response is a list of objects as per the provided example
    for record in external_response:
        fetched_id = fetched_data_counter
        fetched_data_counter += 1
        fetched_record = {
            "fetched_data_id": fetched_id,
            "datasource_id": ds_id,
            "data": record,
            "fetched_at": current_timestamp()
        }
        fetched_data_store[fetched_id] = fetched_record
        fetched_ids.append(fetched_id)
        # Fire and forget processing task for each fetched record (if any additional processing is required)
        asyncio.create_task(process_entity(str(uuid4()), record))  # TODO: Replace record with proper data object if needed.

    # Mark job as completed (for demonstration purposes)
    entity_jobs[job_id]["status"] = "completed"

    result = {
        "datasource_id": ds_id,
        "records_fetched": len(fetched_ids),
        "fetched_data_ids": fetched_ids,
        "message": "Data fetched and persisted successfully"
    }
    return jsonify(result)

@app.route("/datasources/<int:ds_id>/fetched_data", methods=["GET"])
async def get_fetched_data(ds_id):
    # Filter fetched data by datasource_id
    records = [v for v in fetched_data_store.values() if v["datasource_id"] == ds_id]
    return jsonify(records)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)