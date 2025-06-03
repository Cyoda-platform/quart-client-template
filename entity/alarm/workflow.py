import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def process_creation(entity):
    # Add creation timestamp if not present
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()

async def process_status(entity):
    # Ensure status is active
    if "status" not in entity:
        entity["status"] = "active"

async def process_end_time(entity):
    # Calculate end_time if not set
    if "end_time" not in entity and "start_time" in entity and "duration_seconds" in entity:
        start_time = datetime.fromisoformat(entity["start_time"])
        entity["end_time"] = (start_time + timedelta(seconds=entity["duration_seconds"])).isoformat()

async def process_alarm(entity):
    # Workflow orchestration only
    await process_creation(entity)
    await process_status(entity)
    await process_end_time(entity)