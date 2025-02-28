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

def process_add_timestamp(entity):
    # Add a processing timestamp to indicate workflow was applied.
    entity["workflow_processed_at"] = current_timestamp()

def process_validate_entity(entity):
    # Validate mandatory fields are well-formed.
    if not entity.get("datasource_name"):
        raise ValueError("Missing datasource_name")

def process_enrich_entity(entity):
    # Enrich the entity if needed.
    # Example (commented out): 
    # supplementary = {"datasource_id": entity.get("technical_id"), "info": "supplementary"}
    # entity["supplementary"] = supplementary
    pass