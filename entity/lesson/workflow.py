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

def process_set_booked_at(entity):
    # Set the booking timestamp on the entity
    entity["booked_at"] = time.time()
    return entity

def process_set_status(entity):
    # Set the default status of the entity
    entity["status"] = "pending"
    return entity