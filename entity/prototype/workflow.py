import logging
import datetime
from quart import Quart, request, jsonify
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_prototype(entity):
    # Orchestrate workflow steps without business logic
    entity['processed_at'] = datetime.datetime.utcnow().isoformat()
    await enrich_prototype(entity)
    await log_prototype_creation(entity)
    return entity

async def enrich_prototype(entity):
    # Business logic to enrich entity
    # Example: add enrichment timestamp
    entity['enriched_at'] = datetime.datetime.utcnow().isoformat()
    # Additional enrichment logic here

async def log_prototype_creation(entity):
    # Business logic to log creation event asynchronously
    logging.info(f"Entity created with id: {entity.get('id')} at {entity.get('processed_at')}")