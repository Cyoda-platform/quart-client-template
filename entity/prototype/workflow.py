import logging
import datetime
from quart import Quart, request, jsonify
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_prototype(entity: dict):
    entity['processed_at'] = datetime.datetime.utcnow().isoformat()
    entity["workflowProcessed"] = True
    return entity

async def enrich_prototype(entity: dict):
    entity['enriched_at'] = datetime.datetime.utcnow().isoformat()
    entity["workflowProcessed"] = True

async def log_prototype_creation(entity: dict):
    logging.info(f"Entity created with id: {entity.get('id')} at {entity.get('processed_at')}")
    entity["workflowProcessed"] = True