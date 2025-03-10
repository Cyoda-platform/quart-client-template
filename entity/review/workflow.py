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

def process_adjust_rating(entity):
    # Validate rating boundaries and adjust if necessary
    rating = entity.get("rating", 0)
    if not (0 <= rating <= 5):
        entity["rating"] = max(0, min(5, rating))
    return entity

def process_set_reviewed_at(entity):
    # Set the reviewed timestamp on the entity
    entity["reviewed_at"] = time.time()
    return entity