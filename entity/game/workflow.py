from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_game(entity: dict):
    # Workflow orchestration only
    if "processed_at" not in entity:
        entity["processed_at"] = datetime.now(timezone.utc).isoformat()

    await process_validate(entity)
    await process_fetch_subscribers(entity)
    await process_notify_subscribers(entity)

    return entity

async def process_validate(entity: dict):
    date = entity.get("date")
    games = entity.get("games")
    if not date or not isinstance(games, list):
        logger.warning("process_validate: missing or invalid 'date' or 'games' in entity")
        # We do not stop workflow, just log warning

async def process_fetch_subscribers(entity: dict):
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        emails = [sub.get("email") for sub in subscribers if "email" in sub]
        entity["subscribers_emails"] = emails
    except Exception as e:
        logger.exception(f"process_fetch_subscribers: Failed to fetch subscribers: {e}")
        entity["subscribers_emails"] = []

async def process_notify_subscribers(entity: dict):
    emails = entity.get("subscribers_emails", [])
    if emails:
        subject = f"NBA Scores for {entity.get('date')}"
        content = format_email_content(entity.get('date'), entity.get('games', []))
        asyncio.create_task(send_email(emails, subject, content))
    else:
        logger.info("process_notify_subscribers: No subscribers found to notify")