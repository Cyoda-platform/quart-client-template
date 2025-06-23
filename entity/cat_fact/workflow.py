import asyncio
import logging

logger = logging.getLogger(__name__)

async def process_send_emails(entity: dict) -> dict:
    fact_text = entity.get("fact")
    if not fact_text:
        logger.warning("Cat fact entity missing 'fact' key")
        return entity

    subscribers = entity.get("subscribers", {})

    async def send_to_sub(sub):
        try:
            await send_email(sub["email"], "Your Weekly Cat Fact 🐱", fact_text)
        except Exception as e:
            logger.error(f"Failed to send email to {sub['email']}: {e}")

    await asyncio.gather(*(send_to_sub(sub) for sub in subscribers.values()))
    entity["emailsSent"] = len(subscribers)
    return entity

async def process_cat_fact(entity: dict) -> dict:
    # Workflow orchestration only
    entity = await process_send_emails(entity)
    return entity

async def send_email(to_email: str, subject: str, body: str):
    # TODO: Implement real email service
    logger.info(f"Sending email to {to_email} with subject '{subject}' and body: {body}")