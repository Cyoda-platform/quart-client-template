import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# External API key and URL template
SPORTS_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

logger = logging.getLogger(__name__)


async def process_log(entity: dict):
    # Log the workflow execution start for the entity.
    logger.info(f"Executing scores workflow for entity: {entity}")
    return entity


async def process_mark_processed(entity: dict):
    # Mark the record as processed.
    entity["processed"] = True
    return entity


async def process_set_processed_at(entity: dict):
    # Set the processed timestamp.
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity


async def process_handle_exception(entity: dict):
    # In case of error, flag the record as not processed.
    entity["processed"] = False
    return entity