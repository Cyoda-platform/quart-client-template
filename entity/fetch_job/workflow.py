import asyncio
import time
import uuid
from dataclasses import dataclass
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request
import aiohttp

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

async def process_build_headers(entity):
    # Build headers from entity data
    headers = {"Accept": "application/json"}
    auth = entity.get("authorization_header")
    if auth:
        headers["Authorization"] = auth
    entity["headers"] = headers
    return entity

async def process_merge_uri_params(entity):
    # Merge uri_params and additional_params
    uri_params = {}
    if isinstance(entity.get("uri_params"), dict):
        uri_params = entity.get("uri_params").copy()
    additional = entity.get("additional_params")
    if isinstance(additional, dict):
        uri_params.update(additional)
    entity["merged_uri_params"] = uri_params
    return entity

async def process_api_fetch(entity):
    # Perform external API call using URL from entity
    url = entity.get("url")
    headers = entity.get("headers", {})
    params = entity.get("merged_uri_params", {})
    json_data = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if content_type.startswith("application/json"):
                json_data = await resp.json()
            else:
                entity["api_response_error"] = "Non-JSON response received"
    if not isinstance(json_data, list):
        json_data = []
    entity["json_data"] = json_data
    return entity

async def process_record_saving(entity):
    # Process each record and persist using external service
    datasource_name = entity.get("datasource_name")
    count = 0
    json_data = entity.get("json_data", [])
    for record in json_data:
        try:
            record["datasource_name"] = datasource_name
            await entity_service.add_item(
                token=cyoda_token,
                # entity_model="persisted_data",
                entity_model=datasource_name,
                entity_version=ENTITY_VERSION,
                entity=record,
                workflow=process_persisted_data
            )
            count += 1
        except Exception as rec_e:
            continue
    entity["fetched_count"] = count
    return entity

async def process_update_success(entity):
    # Update fetch job entity state as successful
    entity["status"] = "completed"
    entity["completed_at"] = time.time()
    return entity

async def process_persisted_data(entity):
    # Dummy workflow for persisted data processing; modify as needed.
    return entity