import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

CAT_FACT_API_URL = "https://catfact.ninja/fact"

interaction_metrics = {
    "totalEmailsSent": 0,
    "totalClicks": 0,  # TODO: Implement tracking clicks from emails (placeholder)
    "totalOpens": 0,   # TODO: Implement tracking email opens (placeholder)
}

async def send_email(email: str, subject: str, body: str) -> None:
    # TODO: Replace with real email sending implementation
    logger.info(f"Sending email to {email} with subject '{subject}' and body: {body}")
    await asyncio.sleep(0.1)

async def process_fetch_cat_fact(entity: Dict[str, Any]) -> None:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(CAT_FACT_API_URL, timeout=10)
            response.raise_for_status()
            cat_fact_data = response.json()
            fact_text = cat_fact_data.get("fact", "Cats are mysterious creatures.")
        except Exception:
            logger.exception("Failed to fetch cat fact from external API")
            fact_text = "Cats are mysterious creatures."
    entity["factText"] = fact_text
    entity["sentAt"] = datetime.utcnow().isoformat()
    entity["emailsSent"] = 0

async def process_get_subscribers(entity: Dict[str, Any]) -> list:
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to get subscribers inside cat_fact_sent workflow")
        subscribers = []
    return subscribers

async def process_send_emails(entity: Dict[str, Any], subscribers: list) -> None:
    send_tasks = []
    for sub in subscribers:
        email = sub.get("email")
        if email:
            send_tasks.append(send_email(
                email,
                subject="Your Weekly Cat Fact 🐱",
                body=entity["factText"],
            ))
    send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
    success_count = sum(1 for r in send_results if not isinstance(r, Exception))
    entity["emailsSent"] = success_count
    interaction_metrics["totalEmailsSent"] += success_count

async def process_log_cat_fact(entity: Dict[str, Any]) -> None:
    cat_fact_log_entity = {
        "factText": entity["factText"],
        "sentAt": entity["sentAt"],
        "emailsSent": entity["emailsSent"],
        "factId": str(uuid.uuid4()),
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_fact_log",
            entity_version=ENTITY_VERSION,
            entity=cat_fact_log_entity,
            workflow=None,
        )
    except Exception:
        logger.exception("Failed to add cat_fact_log entity in cat_fact_sent workflow")

async def process_cat_fact_sent(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    await process_fetch_cat_fact(entity)
    subscribers = await process_get_subscribers(entity)
    await process_send_emails(entity, subscribers)
    await process_log_cat_fact(entity)
    logger.info(f"Cat fact sent to {entity['emailsSent']} subscribers with fact: {entity['factText']}")
    return entity