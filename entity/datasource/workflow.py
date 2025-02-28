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

async def process_add_timestamp(entity):
    # Business logic: add processing timestamp to the entity
    entity["processed_at"] = time.time()
    return entity