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

def process_normalize_email(entity):
    if "email" in entity and isinstance(entity["email"], str):
        entity["email"] = entity["email"].strip().lower()
    else:
        entity["email"] = ""

def process_set_workflow_flags(entity):
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"