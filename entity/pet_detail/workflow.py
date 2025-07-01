import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def action_start_processing(entity: dict):
    entity['status'] = 'processing_started'
    entity['workflowProcessed'] = True

async def action_update_status_error(entity: dict):
    entity['status'] = 'error'
    entity['workflowProcessed'] = True

async def action_update_status_done(entity: dict):
    entity['status'] = 'done'
    entity['workflowProcessed'] = True

async def cond_has_error(entity: dict) -> bool:
    return entity.get('status') == 'error'

async def cond_is_queued(entity: dict) -> bool:
    return entity.get('status') == 'queued'

async def cond_is_processing(entity: dict) -> bool:
    return entity.get('status') == 'processing'