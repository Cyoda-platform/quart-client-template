import asyncio
import datetime

from uuid import uuid4
from dataclasses import dataclass

import aiohttp
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

def current_timestamp():
    return datetime.datetime.utcnow().isoformat() + "Z"

def process_add_workflow_timestamp(entity):
    # Add a processing timestamp to the entity.
    entity["workflow_processed_at"] = current_timestamp()

async def process_simulate_processing(entity):
    # Simulate additional asynchronous processing.
    await asyncio.sleep(0.1)

def process_mark_as_processed(entity):
    # Mark the record as processed.
    entity["status"] = "processed"

def process_enrich_extraction_meta(entity):
    # Enrich the entity with raw extraction metadata.
    entity["extraction_meta"] = {"extracted_at": current_timestamp()}