import asyncio
import aiohttp
import logging
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Business logic functions

def process_initialize(entity):
    # Initialize cyoda and update entity state
    init_cyoda()
    entity['cyoda_initialized'] = True

def process_generate_token(entity):
    # Generate and assign token to entity
    entity['token'] = cyoda_token

async def process_call_external_service(entity):
    # Call an external service and store the response in the entity
    async with aiohttp.ClientSession() as session:
        async with session.get("https://example.com/api") as response:
            result = await response.text()
            entity['external_response'] = result

def process_update_entity_data(entity):
    # Update entity with processed flag
    entity['processed'] = True

# Workflow orchestration function

@app.route("/activity_logs", methods=["POST"])
@validate_request({})
async def process_activity_logs(entity: dict):
    process_initialize(entity)
    process_generate_token(entity)
    await process_call_external_service(entity)
    process_update_entity_data(entity)
    return jsonify(entity)

if __name__ == "__main__":
    app.run()