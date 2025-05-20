import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Signup:
    email: str

entity_name = "subscriber"  # underscore lowercase entity name

async def process_fetch_cat_fact(entity: Dict) -> None:
    CAT_FACT_API = "https://catfact.ninja/fact"
    fact = "Cats are mysterious creatures!"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_FACT_API, timeout=10)
            response.raise_for_status()
            fact_resp = response.json()
            if isinstance(fact_resp, dict) and "fact" in fact_resp:
                fact = fact_resp["fact"]
    except Exception as e:
        logger.warning(f"Failed to fetch cat fact: {e}")
    entity["cat_fact"] = fact

async def process_update_last_fact(entity: Dict) -> None:
    # Instead of entity_service calls, modify entity state directly
    # Persisted later by Cyoda platform
    entity["last_fact"] = entity.get("cat_fact", "")

async def process_fetch_subscribers(entity: Dict) -> None:
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        emails = [sub.get("email") for sub in subscribers if sub.get("email")]
        entity["emails"] = list(set(emails))  # deduplicate
    except Exception as e:
        logger.warning(f"Failed to fetch subscribers for weekly task: {e}")
        entity["emails"] = []

async def process_send_emails(entity: Dict) -> None:
    emails = entity.get("emails", [])

    async def send_email(to_email: str):
        logger.info(f"Sending email to {to_email} with subject 'Your Weekly Cat Fact 🐱'")
        await asyncio.sleep(0.1)  # simulate send delay
        # TODO: integrate real email sending here
        return True

    send_results = await asyncio.gather(*(send_email(email) for email in emails), return_exceptions=True)
    sent_count = sum(1 for r in send_results if r is True)
    entity["emails_sent"] = sent_count

async def process_update_metrics(entity: Dict) -> None:
    # Instead of entity_service calls, update metrics directly in entity
    prev_count = entity.get("metrics_emails_sent", 0)
    entity["metrics_emails_sent"] = prev_count + entity.get("emails_sent", 0)

async def process_set_task_completed(entity: Dict) -> None:
    entity["taskCompletedAt"] = datetime.utcnow().isoformat()

async def process_weekly_task(entity: Dict) -> None:
    # Workflow orchestration only - no business logic here
    await process_fetch_cat_fact(entity)
    await process_update_last_fact(entity)
    await process_fetch_subscribers(entity)
    await process_send_emails(entity)
    await process_update_metrics(entity)
    await process_set_task_completed(entity)