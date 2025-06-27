import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

async def fetch_cat_fact() -> Optional[str]:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.warning("Cat fact API returned no fact")
                return None
            return fact
        except Exception:
            logger.exception("Failed to fetch cat fact")
            return None

async def send_email_stub(email: str, subject: str, body: str) -> bool:
    # TODO: Replace this stub with real email sending logic (SMTP / API)
    logger.info(f"Sending email to {email} with subject '{subject}' and body:\n{body}")
    await asyncio.sleep(0.05)
    return True

async def _send_welcome_email(entity: dict):
    subject = "Welcome to Cat Facts Newsletter \u001f\u001f"
    body = f"Hello {entity.get('name') or 'Subscriber'},\n\n" \
           f"Thank you for subscribing! Here's a fun cat fact to start:\n\n{entity.get('welcome_cat_fact') or 'Cats are great!'}\n\nEnjoy!"
    try:
        await send_email_stub(entity.get("email"), subject, body)
    except Exception:
        logger.exception("Failed to send welcome email")

async def process_subscriber(entity_data: dict) -> None:
    # Workflow orchestration only - no business logic here
    if "subscribed_at" not in entity_data:
        entity_data["subscribed_at"] = datetime.utcnow().isoformat()
    if "status" not in entity_data:
        entity_data["status"] = "active"

    # Business logic delegated to helper functions
    cat_fact = await fetch_cat_fact()
    if cat_fact:
        entity_data["welcome_cat_fact"] = cat_fact

    # Fire and forget sending welcome email; no await here to avoid blocking
    asyncio.create_task(_send_welcome_email(entity_data))