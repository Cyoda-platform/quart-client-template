import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def process_pet(entity: dict):
    try:
        # Simulate processing the pet search
        search_result = await cyoda_auth_service.search_pet(entity.get("search_criteria", {}))
        entity["search_result"] = search_result
        entity["workflowProcessed"] = True
    except Exception as e:
        logger.exception(e)
        entity["search_result"] = None
        entity["workflowProcessed"] = False

async def is_search_completed(entity: dict) -> bool:
    try:
        result = entity.get("search_result")
        return result is not None and result.get("status") == "completed"
    except Exception as e:
        logger.exception(e)
        return False

async def is_search_failed(entity: dict) -> bool:
    try:
        result = entity.get("search_result")
        return result is not None and result.get("status") == "failed"
    except Exception as e:
        logger.exception(e)
        return False