import asyncio
from datetime import datetime
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
import aiohttp

from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

def process_set_workflow_flag(entity: dict) -> dict:
    # Set the workflowProcessed flag to True.
    entity["workflowProcessed"] = True
    return entity

def process_set_workflow_timestamp(entity: dict) -> dict:
    # Set the workflowProcessedAt timestamp.
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat()
    return entity