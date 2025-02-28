import asyncio
import datetime
import uuid

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # TODO: Consider adding request validation in a complete solution

# In-memory persistence mocks
datasources = {}       # key: technical_id, value: datasource details
fetched_data = {}      # key: datasource technical_id, value: list of fetched external records

# Data Source Management Endpoints

@app.route('/datasources', methods=['POST'])
async def create_datasource():
    req = await request.get_json()
    if not req.get('datasource_name') or not req.get('url'):
        abort(400, "datasource_name and url are required")
    technical_id = str(uuid.uuid4())
    datasource = {
        "technical_id": technical_id,
        "datasource_name": req["datasource_name"],
        "url": req["url"],
        "uri_params": req.get("uri_params", {}),
        "authorization_header": req.get("authorization_header", ""),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    datasources[technical_id] = datasource
    return jsonify(datasource), 201

@app.route('/datasources', methods=['GET'])
async def get_datasources():
    return jsonify(list(datasources.values()))

@app.route('/datasources/<technical_id>', methods=['GET'])
async def get_datasource(technical_id):
    datasource = datasources.get(technical_id)
    if not datasource:
        abort(404, "Datasource not found")
    return jsonify(datasource)

@app.route('/datasources/<technical_id>', methods=['PUT'])
async def update_datasource(technical_id):
    datasource = datasources.get(technical_id)
    if not datasource:
        abort(404, "Datasource not found")
    req = await request.get_json()
    for key in ['datasource_name', 'url', 'uri_params', 'authorization_header']:
        if key in req:
            datasource[key] = req[key]
    return jsonify(datasource)

@app.route('/datasources/<technical_id>', methods=['DELETE'])
async def delete_datasource(technical_id):
    if technical_id in datasources:
        del datasources[technical_id]
        # Remove related fetched data if exists.
        fetched_data.pop(technical_id, None)
        return '', 204
    else:
        abort(404, "Datasource not found")

# External API Data Fetch and Persistence

async def process_fetch(datasource):
    # Prepare headers and parameters
    headers = {"Accept": "application/json"}
    if datasource.get("authorization_header"):
        headers["Authorization"] = datasource["authorization_header"]
    
    url = datasource["url"]
    params = datasource.get("uri_params", {})

    # Make GET request to the external API using aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    # TODO: Enhance error handling and retries if needed.
                    return None
                data = await resp.json()
        except Exception as e:
            # TODO: Log exception and handle unexpected errors.
            return None

    # Persist the fetched data in the local cache.
    fetched_data.setdefault(datasource["technical_id"], [])
    if isinstance(data, list):
        fetched_data[datasource["technical_id"]].extend(data)
        return len(data)
    else:
        # TODO: Handle cases where response is not a list (e.g., dict or unexpected format).
        fetched_data[datasource["technical_id"]].append(data)
        return 1

@app.route('/datasources/<technical_id>/fetch', methods=['POST'])
async def fetch_datasource_data(technical_id):
    datasource = datasources.get(technical_id)
    if not datasource:
        abort(404, "Datasource not found")

    # Fire and forget processing task.
    # TODO: In a full implementation, consider using background task processing.
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
    if technical_id not in datasources:
        abort(404, "Datasource not found")
    data = fetched_data.get(technical_id, [])
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)