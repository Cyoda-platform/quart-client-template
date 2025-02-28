import asyncio
import datetime
import uuid
from dataclasses import dataclass, field

from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Workaround: For GET endpoints with query parameters validation must be first, but here only POST/PUT use validation.

# In-memory persistence mocks
datasources = {}       # key: technical_id, value: datasource details
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

# Data Source Management Endpoints

@app.route('/datasources', methods=['POST'])
@validate_request(CreateDatasource)  # For POST, validation decorator goes second
async def create_datasource(data: CreateDatasource):
    if not data.datasource_name or not data.url:
        abort(400, "datasource_name and url are required")
    technical_id = str(uuid.uuid4())
    datasource = {
        "technical_id": technical_id,
        "datasource_name": data.datasource_name,
        "url": data.url,
        "uri_params": data.uri_params,
        "authorization_header": data.authorization_header,
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
@validate_request(UpdateDatasource)  # For PUT, validation decorator goes second
async def update_datasource(data: UpdateDatasource, technical_id):
    datasource = datasources.get(technical_id)
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
    return jsonify(datasource)

@app.route('/datasources/<technical_id>', methods=['DELETE'])
async def delete_datasource(technical_id):
    if technical_id in datasources:
        del datasources[technical_id]
        fetched_data.pop(technical_id, None)
        return '', 204
    else:
        abort(404, "Datasource not found")

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
                    # TODO: Enhance error handling and retries if needed.
                    return None
                data = await resp.json()
        except Exception as e:
            # TODO: Log exception and handle unexpected errors.
            return None

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