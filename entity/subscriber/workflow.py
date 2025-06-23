import asyncio
import logging

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, body: str):
    # TODO: Implement real email service
    logger.info(f"Sending email to {to_email} with subject '{subject}' and body: {body}")

async def process_fetch_and_send_fact(entity: dict):
    # This function fetches a cat fact and updates the entity with it
    from httpx import AsyncClient
    try:
        async with AsyncClient() as client:
            response = await client.get("https://catfact.ninja/fact", timeout=10)
            response.raise_for_status()
            data = response.json()
            fact = data.get("fact", "No fact retrieved")
            entity["fact"] = fact
            entity["fetchedAt"] = response.headers.get("Date", "")
            entity["status"] = "fact_fetched"
    except Exception as e:
        logger.error(f"Failed to fetch cat fact: {e}")
        entity["status"] = "fetch_failed"

async def process_send_emails(entity: dict):
    # This function sends the fetched cat fact to all subscribers stored in entity['subscribers']
    fact = entity.get("fact", "")
    subscribers = entity.get("subscribers", {})
    sent_count = 0
    for sub_id, subscriber in subscribers.items():
        email = subscriber.get("email")
        if email:
            try:
                await send_email(email, "Your Weekly Cat Fact 🐱", fact)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email to {email}: {e}")
    entity["emailsSent"] = sent_count
    entity["status"] = "emails_sent"

async def process_track_interactions(entity: dict):
    # This function counts interactions and updates entity with totals
    interactions = entity.get("interactions", [])
    total_opens = sum(1 for i in interactions if i.get("interactionType") == "open")
    total_clicks = sum(1 for i in interactions if i.get("interactionType") == "click")
    entity["totalOpens"] = total_opens
    entity["totalClicks"] = total_clicks
    entity["status"] = "interactions_tracked"

async def process_subscriber(entity: dict):
    # Orchestrates the workflow for subscriber entity
    if entity.get("state") == "new":
        # e.g. send welcome email
        email = entity.get("email")
        name = entity.get("name", "")
        if email:
            try:
                await send_email(email, "Welcome to Cat Facts Newsletter",
                                 f"Hello {name or 'subscriber'}, thank you for subscribing!")
                entity["welcomeEmailSent"] = True
            except Exception as e:
                logger.error(f"Failed to send welcome email to {email}: {e}")
                entity["welcomeEmailSent"] = False
        entity["state"] = "active"
    # no other orchestration here, business logic in other process_* funcs
    return entity