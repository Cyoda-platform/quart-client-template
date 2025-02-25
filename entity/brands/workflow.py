import asyncio
import aiohttp
import logging
from dataclasses import dataclass

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)

def process_set_processed(entity):
    # Set the processed flag on the entity.
    entity["processed"] = True

def process_add_metadata(entity):
    # Add metadata and set a processed timestamp.
    if "metadata" not in entity:
        entity["metadata"] = {}
    entity["metadata"]["processed_timestamp"] = asyncio.get_event_loop().time()

async def process_log_entity_activity(entity):
    try:
        # Prepare supplementary data for logging.
        log_data = {
            "brand_id": entity.get("id"),
            "status": "processed",
            "message": "Entity processed and stored successfully."
        }
        # Persist the log as a supplementary entity of a different model.
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="activity_logs",
            entity_version=ENTITY_VERSION,
            entity=log_data,
            workflow=None
        )
        logger.info("Activity log created for brand id: %s", entity.get("id"))
    except Exception as ex:
        logger.error("Failed to log entity activity: %s", ex)