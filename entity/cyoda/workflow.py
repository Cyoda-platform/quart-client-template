import logging
import time
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()['cyoda_auth_service']

async def can_process(entity: dict) -> bool:
    return 'id' in entity and entity['id'] is not None

async def process_cyoda(entity: dict):
    entity['processed_timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    try:
        supplementary_items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="supplementary_model",
            entity_version=ENTITY_VERSION
        )
        count = len(supplementary_items) if supplementary_items else 0
        entity['supplementary_count'] = count
    except Exception as e:
        logger.exception(e)
    return entity