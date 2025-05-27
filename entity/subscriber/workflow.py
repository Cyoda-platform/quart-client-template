import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

async def process_subscriber(entity: Dict) -> None:
    if "email" in entity and entity["email"]:
        entity["email"] = entity["email"].strip().lower()
    await process_send_welcome_email(entity)

async def process_send_welcome_email(entity: Dict) -> None:
    try:
        logger.info(f"Sending welcome email to {entity.get('email')}")
        # Replace with real email sending logic
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.warning(f"Failed to send welcome email to {entity.get('email')}: {e}")