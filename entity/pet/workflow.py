import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def is_search_id_generated(entity: dict) -> bool:
    try:
        return 'search_id' in entity and entity['search_id'] is not None and entity['search_id'] != ''
    except Exception as e:
        logger.exception(e)
        return False

async def is_pet_search_result_status_queued(entity: dict) -> bool:
    try:
        return entity.get('status') == 'queued'
    except Exception as e:
        logger.exception(e)
        return False

async def is_pet_search_result_status_error(entity: dict) -> bool:
    try:
        return entity.get('status') == 'error'
    except Exception as e:
        logger.exception(e)
        return False

async def is_pet_search_result_status_done(entity: dict) -> bool:
    try:
        return entity.get('status') == 'done'
    except Exception as e:
        logger.exception(e)
        return False

async def create_pet_search_result_entity(entity: dict):
    try:
        # Assuming creation means setting up initial fields for search result entity
        if 'search_id' not in entity or not entity['search_id']:
            entity['search_id'] = None
        entity['status'] = 'initialized'
        entity['workflowProcessed'] = True
        entity['version'] = ENTITY_VERSION
    except Exception as e:
        logger.exception(e)

async def start_background_pet_search(entity: dict):
    try:
        # simulate starting background search, e.g. setting status to processing
        entity['status'] = 'processing'
        entity['workflowProcessed'] = True
        entity['version'] = ENTITY_VERSION
    except Exception as e:
        logger.exception(e)

async def handle_search_error(entity: dict):
    try:
        # handle error by setting status to error and logging error details if any
        entity['status'] = 'error'
        entity['workflowProcessed'] = True
        entity['version'] = ENTITY_VERSION
    except Exception as e:
        logger.exception(e)