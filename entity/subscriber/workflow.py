from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_subscriber(entity: dict) -> dict:
    """Workflow orchestration for subscriber entity."""
    entity['subscribed_at'] = datetime.utcnow().isoformat()
    await process_send_welcome_email(entity)
    return entity

async def process_send_welcome_email(entity: dict):
    try:
        await send_email(
            [entity['email']],
            "Welcome to NBA Scores Notification",
            "Thank you for subscribing to NBA scores notifications!"
        )
    except Exception:
        logger.exception("Failed to send welcome email")

async def process_fetch_scores(entity: dict):
    """Fetch NBA scores from external API and store in entity['games']."""
    date = entity.get('date')
    if not date:
        entity['status'] = 'error'
        return entity
    try:
        games = await fetch_nba_scores(date)
        entity['games'] = games
        entity['status'] = 'fetched'
    except Exception:
        logger.exception(f"Failed to fetch NBA scores for {date}")
        entity['status'] = 'error'
    return entity

async def process_send_notifications(entity: dict):
    """Send notification emails to subscribers with games summary."""
    subscribers = entity.get('subscribers', [])
    date = entity.get('date')
    games = entity.get('games', [])
    if not subscribers:
        entity['notification_status'] = 'no_subscribers'
        return entity
    try:
        body = build_email_body(date, games)
        subject = f"NBA Scores for {date}"
        await send_email(subscribers, subject, body)
        entity['notification_status'] = 'sent'
    except Exception:
        logger.exception(f"Failed to send notifications for {date}")
        entity['notification_status'] = 'error'
    return entity

async def process_fetch_store_notify(entity: dict):
    """Orchestrates fetching, storing and notifying workflow on entity."""
    await process_fetch_scores(entity)
    await process_send_notifications(entity)
    entity['workflow_completed_at'] = datetime.utcnow().isoformat()
    return entity