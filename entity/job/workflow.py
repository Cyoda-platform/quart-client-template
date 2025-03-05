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

# Process functions for job entity

async def process_log_job(entity: dict):
    # Log the start of the job workflow.
    logger.info(f"Executing job workflow for entity: {entity}")
    return entity

async def process_simulate_delay(entity: dict):
    # Simulate processing delay if needed.
    await asyncio.sleep(1)
    return entity

async def process_extract_external_data(entity: dict):
    # Extract external_data attached by the controller and remove it from the entity.
    external_data = entity.pop("external_data", [])
    entity["extracted_external_data"] = external_data
    if not external_data:
        logger.warning("No external data found in job entity; skipping scores creation.")
    return entity

async def process_build_scores_payload(entity: dict):
    # Construct scores payload from job entity and extracted external data.
    if entity.get("extracted_external_data"):
        scores_payload = {"date": entity.get("date"), "games": entity["extracted_external_data"]}
        entity["scores_payload"] = scores_payload
    return entity

async def process_add_scores(entity: dict):
    # Persist the scores entity using its workflow if scores_payload is available.
    if "scores_payload" in entity:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="scores",
            entity_version=ENTITY_VERSION,
            entity=entity["scores_payload"],
            workflow=process_scores  # Workflow function for scores entity.
        )
    return entity

async def process_update_job_success(entity: dict):
    # Update job entity state to reflect a successful outcome.
    entity["status"] = "completed"
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

async def process_log_success(entity: dict):
    # Log job completion.
    record_count = len(entity.get("extracted_external_data", []))
    logger.info(f"Job processed for date {entity.get('date')}, records processed: {record_count}.")
    return entity

async def process_update_job_failure(entity: dict):
    # Update job entity state to reflect a failure.
    entity["status"] = "failed"
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

# Process functions for scores entity

async def process_log_scores(entity: dict):
    # Log the start of the scores workflow.
    logger.info(f"Executing scores workflow for entity: {entity}")
    return entity

async def process_mark_scores(entity: dict):
    # Mark the scores record as processed.
    entity["processed"] = True
    return entity

async def process_set_scores_timestamp(entity: dict):
    # Set the processed timestamp for the scores entity.
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

async def process_handle_scores_exception(entity: dict):
    # In case of error, flag the scores record.
    entity["processed"] = False
    return entity

# Workflow orchestration for the scores entity.
async def process_scores(entity: dict):
    try:
        await process_log_scores(entity)
        await process_mark_scores(entity)
        await process_set_scores_timestamp(entity)
    except Exception as e:
        logger.exception(e)
        await process_handle_scores_exception(entity)
    return entity