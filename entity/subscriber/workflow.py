import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def send_email(email: str, subject: str, body: str) -> None:
    # TODO: Replace with real email sending implementation
    logger.info(f"Sending email to {email} with subject '{subject}' and body: {body}")
    await asyncio.sleep(0.1)

async def process_send_welcome_email(entity: Dict[str, Any]) -> None:
    email = entity.get("email")
    if not email:
        return
    try:
        await send_email(
            email,
            subject="Welcome to Cat Facts!",
            body="Thank you for subscribing to Cat Facts!"
        )
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        logger.exception(f"Failed to send welcome email to {email}: {e}")

async def process_normalize_email(entity: Dict[str, Any]) -> None:
    email = entity.get("email")
    if email:
        entity["email"] = email.lower()

async def process_set_subscribed_at(entity: Dict[str, Any]) -> None:
    if "subscribedAt" not in entity:
        entity["subscribedAt"] = datetime.utcnow().isoformat()

async def process_subscriber(entity: Dict[str, Any]) -> Dict[str, Any]:
    await process_normalize_email(entity)
    await process_set_subscribed_at(entity)
    # Fire and forget welcome email sending
    asyncio.create_task(process_send_welcome_email(entity))
    return entity