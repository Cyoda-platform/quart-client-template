from datetime import datetime
import asyncio
import aiohttp
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda  # assume async or sync as needed

# Business logic functions – each takes one entity argument and directly modifies it.

async def process_initialize_entity(entity):
    # Set initial attributes for the entity.
    entity['initialized'] = True
    entity['timestamp'] = datetime.utcnow().isoformat()
    entity['uuid'] = str(uuid.uuid4())

async def process_set_token(entity):
    # Set token value using the imported cyoda_token.
    entity['token'] = cyoda_token

async def process_init_cyoda_connection(entity):
    # Initialize the cyoda connection.
    await init_cyoda()
    entity['cyoda_initialized'] = True

async def process_fetch_brands_data(entity):
    # Fetch brands data from an external API endpoint.
    url = "https://example.com/api/brands"  # Replace with a real endpoint as needed.
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            entity['brands_data'] = data

async def process_calculate_summary(entity):
    # Calculate a summary based on the fetched brands data.
    data = entity.get('brands_data', [])
    summary = {"count": len(data)}
    entity['brands_summary'] = summary

# Workflow orchestration – no business logic here.
async def process_brands_summary(entity):
    await process_initialize_entity(entity)
    await process_set_token(entity)
    await process_init_cyoda_connection(entity)
    await process_fetch_brands_data(entity)
    await process_calculate_summary(entity)
    
# Below is an example Quart endpoint to use the workflow.
app = Quart(__name__)
QuartSchema(app)

@app.route('/brands-summary', methods=['POST'])
@validate_request(json=True)
async def brands_summary_endpoint():
    entity = await request.get_json()
    await process_brands_summary(entity)
    return jsonify(entity)