import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import List, Optional
import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

API_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={api_key}"

async def process_subscribe_request(entity: dict) -> dict:
    logger.info(f"Running workflow on subscribe_request entity: {entity}")

    # Orchestrate the workflow steps
    await process_validate_subscription(entity)
    await process_update_subscription(entity)
    await process_notify_subscription_change(entity)

    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

async def process_validate_subscription(entity: dict):
    email = entity.get("email")
    notification_type = entity.get("notificationType", "").lower()
    if not email or notification_type not in ("summary", "full"):
        entity["error"] = "Invalid subscription data"
        logger.error(f"Validation failed for subscription entity: {entity}")
        return
    entity["notificationType"] = notification_type

async def process_update_subscription(entity: dict):
    # Directly modify entity state for subscription update
    # Here entity is assumed to represent subscriber data
    # In a real app, this would interface with a DB or cache
    entity["subscribed"] = True
    logger.info(f"Subscription updated for: {entity.get('email')}")

async def process_notify_subscription_change(entity: dict):
    # Send notification email or other side effects
    # TODO: Implement actual notification sending
    logger.info(f"Notification sent for subscription change: {entity.get('email')}")