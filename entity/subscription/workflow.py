import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_subscription(entity: dict):
    # Workflow orchestration only
    await process_add_subscription_timestamp(entity)
    await process_send_confirmation_email(entity)
    return entity

async def process_add_subscription_timestamp(entity: dict):
    entity["subscribed_at"] = datetime.utcnow().isoformat()

async def process_send_confirmation_email(entity: dict):
    email = entity.get("email")
    if email:
        # Fire and forget sending confirmation email
        asyncio.create_task(send_email(
            to_email=email,
            subject="Subscription Confirmation",
            body="Thank you for subscribing!"
        ))

# Placeholder for send_email function to avoid errors in this snippet
async def send_email(to_email: str, subject: str, body: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")