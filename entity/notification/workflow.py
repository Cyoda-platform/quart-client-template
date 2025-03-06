import asyncio
import datetime
import logging

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)

async def send_email_notification(email: str, subject: str, body: str):
    try:
        logger.info(f"Sending email to {email} with subject '{subject}'")
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.exception(e)
    return True

async def process_set_timestamp(entity: dict):
    try:
        entity["notified_at"] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
    return entity

async def process_get_subscribers(entity: dict):
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        subscribers = []
    entity["subscribers"] = subscribers
    return entity

async def process_send_notifications(entity: dict):
    try:
        subject = entity.get("subject", "Notification")
        body = entity.get("body", "")
        subscribers = entity.get("subscribers", [])
        for subscriber in subscribers:
            email = subscriber.get("email")
            if email:
                asyncio.create_task(send_email_notification(email, subject, body))
    except Exception as e:
        logger.exception(e)
    return entity