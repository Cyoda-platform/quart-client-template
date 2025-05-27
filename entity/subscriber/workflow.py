from typing import Dict
import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_subscriber(entity: Dict) -> None:
    # Workflow orchestration for subscriber entity
    await process_normalize_email(entity)
    await process_validate_notification_type(entity)

async def process_normalize_email(entity: Dict) -> None:
    # Normalize email to lowercase and strip spaces
    email = entity.get("email")
    if email:
        entity["email"] = email.strip().lower()

async def process_validate_notification_type(entity: Dict) -> None:
    # Ensure notificationType is valid, default to 'summary' if missing or invalid
    nt = entity.get("notificationType", "summary").lower()
    if nt not in ("summary", "full"):
        nt = "summary"
    entity["notificationType"] = nt