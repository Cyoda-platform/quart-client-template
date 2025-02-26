from common.grpc_client.grpc_client import grpc_stream
from datetime import datetime
import asyncio
import uuid
import aiohttp
from dataclasses import dataclass

from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Initialize Quart app and schema
app = Quart(__name__)
QuartSchema(app)

EXTERNAL_API_URL = "https://test-api.k6.io/public/crocodiles/"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
    except Exception as e:
        print(f"Error during cyoda initialization: {e}")
        raise e

# Dummy dataclass for ingestion endpoint (no payload expected)
@dataclass
class IngestRequest:
    dummy: str = ""

# Dataclass for filter endpoint
@dataclass
class FilterCrocodilesRequest:
    name: str = ""
    sex: str = ""
    min_age: int = 0
    max_age: int = 200

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)  # Validate request payload.
async def ingest_crocodiles(data: IngestRequest):
    try:
        # Retrieve data from the external API.
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL) as resp:
                if resp.status != 200:
                    abort(resp.status, description="Failed to fetch external data")
                external_data = await resp.json()
    except Exception as e:
        print(f"Error fetching external data: {e}")
        abort(500, description="Error fetching external data")

    try:
        # Use the external entity_service with the workflow function.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="crocodiles",
            entity_version=ENTITY_VERSION,
            entity=external_data,
            )
    except Exception as e:
        print(f"Error adding item to entity_service: {e}")
        abort(500, description="Error persisting entity")
    
    # Return only the id.
    return jsonify({
        "status": "success",
        "id": new_id
    })

@app.route('/api/crocodiles/filter', methods=['POST'])
@validate_request(FilterCrocodilesRequest)
async def filter_crocodiles(data: FilterCrocodilesRequest):
    condition = {
        "name": data.name,
        "sex": data.sex,
        "min_age": data.min_age,
        "max_age": data.max_age
    }
    try:
        results = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="crocodiles",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        print(f"Error fetching filtered crocodiles: {e}")
        abort(500, description="Error fetching filtered crocodiles")
    
    return jsonify({
        "status": "success",
        "results": results
    })

@app.route('/api/crocodiles/results', methods=['GET'])
async def get_all_crocodiles():
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="crocodiles",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        print(f"Error fetching crocodiles: {e}")
        abort(500, description="Error fetching crocodiles")
    
    return jsonify({
        "status": "success",
        "data": data
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)