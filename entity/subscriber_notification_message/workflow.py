# ABOUTME: This file contains the workflow processors for subscriber_notification_message entity.
# ABOUTME: It handles sending, retrying, and cancelling individual notification messages to subscribers.

import asyncio
import datetime
import logging
from typing import List, Optional

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)

# Initialize services
factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

def format_email_summary(games_for_date: List[dict]) -> str:
    """Format NBA scores as a summary email."""
    lines = [f"NBA Scores Summary for {games_for_date[0]['Day']}:\n"] if games_for_date else ["NBA Scores Summary:\n"]
    for g in games_for_date:
        lines.append(f"{g['AwayTeam']} @ {g['HomeTeam']} - {g['AwayTeamScore']} : {g['HomeTeamScore']}")
    return "\n".join(lines)

def format_email_full(games_for_date: List[dict]) -> str:
    """Format NBA scores as a full HTML email."""
    html = [f"<h1>NBA Scores for {games_for_date[0]['Day']}</h1><ul>"] if games_for_date else ["<h1>NBA Scores</h1><ul>"]
    for g in games_for_date:
        html.append(
            f"<li><b>{g['AwayTeam']} @ {g['HomeTeam']}</b>: {g['AwayTeamScore']} - {g['HomeTeamScore']}<br>"
            f"Status: {g.get('Status', 'N/A')}, Quarter: {g.get('Quarter', 'N/A')}, Time Remaining: {g.get('TimeRemaining', 'N/A')}</li>"
        )
    html.append("</ul>")
    return "".join(html)

async def send_email(email: str, subject: str, body: str, html: bool = False):
    """Send email notification to subscriber."""
    # TODO: implement actual email sending
    logger.info(f"Sending {'HTML' if html else 'plain text'} email to {email}:\nSubject: {subject}\n{body}")

async def process_send_notification(entity: dict) -> dict:
    """Process sending notification to a subscriber."""
    logger.info(f"Processing send notification for entity: {entity}")
    
    subscriber_email = entity.get("subscriber_email")
    notification_type = entity.get("notification_type")
    date = entity.get("date")
    scores_data = entity.get("scores_data", [])
    
    if not subscriber_email or not notification_type or not date:
        entity["status"] = "failed"
        entity["error_message"] = "Missing required fields: subscriber_email, notification_type, or date"
        logger.error(f"Missing required fields in notification entity: {entity}")
        return entity
    
    try:
        # Format and send the email based on notification type
        if notification_type == "summary":
            body = format_email_summary(scores_data)
            await send_email(subscriber_email, f"NBA Scores Summary for {date}", body, html=False)
        else:  # full
            body = format_email_full(scores_data)
            await send_email(subscriber_email, f"NBA Scores Full Listing for {date}", body, html=True)
        
        # Update entity status on successful send
        entity["status"] = "sent"
        entity["sent_at"] = datetime.datetime.utcnow().isoformat()
        entity["retry_count"] = entity.get("retry_count", 0)
        logger.info(f"Successfully sent notification to {subscriber_email}")
        
    except Exception as e:
        # Update entity status on failure
        entity["status"] = "failed"
        entity["error_message"] = str(e)
        entity["retry_count"] = entity.get("retry_count", 0)
        entity["last_attempt_at"] = datetime.datetime.utcnow().isoformat()
        logger.exception(f"Failed to send notification to {subscriber_email}: {e}")
    
    return entity

async def process_retry_notification(entity: dict) -> dict:
    """Process retrying a failed notification."""
    logger.info(f"Processing retry notification for entity: {entity}")
    
    max_retries = entity.get("max_retries", 3)
    retry_count = entity.get("retry_count", 0)
    
    if retry_count >= max_retries:
        entity["status"] = "failed_max_retries"
        entity["error_message"] = f"Maximum retry attempts ({max_retries}) exceeded"
        logger.warning(f"Maximum retries exceeded for notification to {entity.get('subscriber_email')}")
        return entity
    
    # Increment retry count
    entity["retry_count"] = retry_count + 1
    
    # Attempt to send again
    return await process_send_notification(entity)

async def process_cancel_notification(entity: dict) -> dict:
    """Process cancelling a notification."""
    logger.info(f"Processing cancel notification for entity: {entity}")
    
    entity["status"] = "cancelled"
    entity["cancelled_at"] = datetime.datetime.utcnow().isoformat()
    logger.info(f"Cancelled notification to {entity.get('subscriber_email')}")
    
    return entity
