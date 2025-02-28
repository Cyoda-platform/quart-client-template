import asyncio
import datetime
import uuid
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

SPORTS_DATA_API_KEY = "f8824354d80d45368063dd2e6fb16c38"

# Business logic: set workflow flag
def process_set_workflow_flag(entity):
    entity["workflowProcessed"] = True

# Business logic: set workflow timestamp
def process_set_workflow_timestamp(entity):
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

# Workflow orchestration: calls business logic functions
def process_scores(entity):
    process_set_workflow_flag(entity)
    process_set_workflow_timestamp(entity)
    return entity