import asyncio
import datetime
import logging

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)

async def process_set_subscription_timestamp(entity: dict):
    try:
        entity["subscribed_at"] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
    return entity