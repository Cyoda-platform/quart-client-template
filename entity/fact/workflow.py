import httpx
from datetime import datetime, timezone
import asyncio
import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()['cyoda_auth_service']

async def is_fact_missing(entity: dict) -> bool:
    return not bool(entity.get("fact"))

async def not_is_fact_missing(entity: dict) -> bool:
    return bool(entity.get("fact"))

async def fetch_cat_fact(entity: dict) -> dict:
    url = "https://catfact.ninja/fact"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            entity["fact"] = data.get("fact", "Cats are mysterious creatures!")
    except Exception as e:
        logger.exception(e)
        entity["fact"] = "Cats are mysterious creatures!"
    return entity

async def is_sent_date_missing(entity: dict) -> bool:
    return "sentDate" not in entity

async def not_is_sent_date_missing(entity: dict) -> bool:
    return "sentDate" in entity

async def add_sent_date(entity: dict) -> dict:
    entity["sentDate"] = datetime.now(timezone.utc).isoformat()
    return entity

async def retrieve_subscribers(entity: dict) -> dict:
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        subscribers = []
    entity["_subscribers_cache"] = subscribers  # temporary cache in entity for next steps
    return entity

async def send_emails_to_subscribers(entity: dict) -> dict:
    subscribers = entity.get("_subscribers_cache", [])

    async def send_email(email: str, fact_text: str):
        try:
            await asyncio.sleep(0.05)  # Simulate sending email
            logger.info(f"Sent cat fact email to {email}")
        except Exception:
            logger.exception(f"Failed to send cat fact email to {email}")

    send_tasks = []
    for sub in subscribers:
        email = sub.get("email")
        if email:
            send_tasks.append(send_email(email, entity.get("fact", "")))

    if send_tasks:
        await asyncio.gather(*send_tasks)

    entity["emailsSent"] = len(send_tasks)
    return entity

async def update_emails_sent_count(entity: dict) -> dict:
    # In prototype, emailsSent is updated directly on entity, so nothing more to do here
    # Keeping method for workflow completeness
    return entity