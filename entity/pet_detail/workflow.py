import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def create_entity(entity: dict):
    try:
        # Example logic to create entity - adapt as per initial code logic
        entity['status'] = 'created'
        entity['workflowProcessed'] = True
        entity['entity_version'] = ENTITY_VERSION
    except Exception as e:
        logger.exception(e)
        raise

async def can_fail_returns_bool(entity: dict) -> bool:
    try:
        # Example condition logic for failure - adapt as per initial code logic
        return entity.get('should_fail', False)
    except Exception as e:
        logger.exception(e)
        return False

async def can_start_processing_returns_bool(entity: dict) -> bool:
    try:
        # Example condition logic to start processing - adapt as per initial code logic
        return entity.get('ready_to_process', False)
    except Exception as e:
        logger.exception(e)
        return False

async def start_processing(entity: dict):
    try:
        # Example logic to start processing - adapt as per initial code logic
        entity['processing_started'] = True
        entity['workflowProcessed'] = True
    except Exception as e:
        logger.exception(e)
        raise

async def can_finish_returns_bool(entity: dict) -> bool:
    try:
        # Example condition logic to finish processing - adapt as per initial code logic
        return entity.get('processing_complete', False)
    except Exception as e:
        logger.exception(e)
        return False