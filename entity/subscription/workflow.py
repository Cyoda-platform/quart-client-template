import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)

# External API key and URL template
SPORTS_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def process_log_subscription(entity: dict):
    # Log the subscription workflow execution.
    logger.info(f"Executing subscription workflow for entity: {entity}")
    return entity

async def process_set_confirmation_flag(entity: dict):
    # Set the email confirmation flag to indicate pending confirmation.
    entity["confirmed"] = False
    return entity

async def process_set_subscription_time(entity: dict):
    # Set the subscribedAt timestamp if not already present.
    entity["subscribedAt"] = entity.get("subscribedAt", datetime.utcnow().isoformat())
    return entity