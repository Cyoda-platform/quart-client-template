from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_subscriber(entity: dict) -> dict:
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.now(timezone.utc).isoformat()

    async def send_welcome_email():
        try:
            await asyncio.sleep(0.05)
            logger.info(f"Welcome email sent to {entity.get('email')}")
        except Exception:
            logger.exception("Failed to send welcome email")

    asyncio.create_task(send_welcome_email())
    return entity

async def is_new_subscriber(entity: dict) -> bool:
    return "createdAt" not in entity

async def has_createdAt(entity: dict) -> bool:
    return "createdAt" in entity