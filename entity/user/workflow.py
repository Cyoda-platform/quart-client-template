import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import List, Any

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION  # constant for entity version
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

def process_set_created_at(entity):
    # Set the created timestamp on the entity
    entity["created_at"] = time.time()
    return entity

def process_set_active(entity):
    # Set the default active flag on the entity
    entity["active"] = True
    return entity

async def process_send_welcome_email(entity):
    # Business logic to send a welcome email if an email address exists
    if "email" in entity:
        # Simulate asynchronous email sending task
        await asyncio.sleep(0)
        # Actual email sending logic would be implemented here
    return entity