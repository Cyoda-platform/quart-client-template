from datetime import datetime
import logging
import asyncio
from uuid import uuid4
import httpx

logger = logging.getLogger(__name__)

async def process_catfact_send_job(entity: dict) -> dict:
    # Workflow orchestration only
    entity = await process_fetch_cat_fact(entity)
    if not entity.get("fact"):
        return entity

    entity = await process_retrieve_subscribers(entity)
    if not entity.get("subscribers"):
        return entity

    entity = await process_send_emails(entity)
    entity = await process_record_send_result(entity)
    return entity

async def process_fetch_cat_fact(entity: dict) -> dict:
    # Business logic: fetch cat fact from external API
    url = "https://catfact.ninja/fact"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if fact:
                entity['fact'] = fact
                logger.info(f"Fetched cat fact: {fact}")
            else:
                logger.error("No fact found in response")
                entity['fact'] = None
    except Exception as e:
        logger.exception(f"Failed to fetch cat fact: {e}")
        entity['fact'] = None
    return entity

async def process_retrieve_subscribers(entity: dict) -> dict:
    # Business logic: retrieve subscribers list from entity_service
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscribe_request",
            entity_version=ENTITY_VERSION
        )
        entity['subscribers'] = subscribers or []
        if not entity['subscribers']:
            logger.info("No subscribers found")
    except Exception as e:
        logger.exception(f"Failed to retrieve subscribers: {e}")
        entity['subscribers'] = []
    return entity

async def process_send_emails(entity: dict) -> dict:
    # Business logic: send cat fact emails asynchronously to subscribers
    fact = entity.get('fact')
    subscribers = entity.get('subscribers', [])
    emails_sent = 0

    async def send_to_subscriber(sub):
        nonlocal emails_sent
        subject = "Your Weekly Cat Fact! 🐱"
        name_part = f" {sub.get('name')}" if sub.get('name') else ""
        body = f"Hello{name_part},\n\nHere's your cat fact this week:\n\n{fact}\n\nEnjoy!"
        try:
            sent = await send_email(sub["email"], subject, body)
            if sent:
                emails_sent += 1
        except Exception as e:
            logger.exception(f"Failed to send email to {sub['email']}: {e}")

    await asyncio.gather(*(send_to_subscriber(sub) for sub in subscribers))
    logger.info(f"Cat fact sent to {emails_sent} subscribers")
    entity['emailsSent'] = emails_sent
    return entity

async def process_record_send_result(entity: dict) -> dict:
    # Business logic: record result of send job (external entity)
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="catfact_send_result",
            entity_version=ENTITY_VERSION,
            entity={
                "jobId": entity.get("id", str(uuid4())),
                "sentAt": datetime.utcnow().isoformat(),
                "emailsSentCount": entity.get("emailsSent", 0),
                "fact": entity.get("fact", "")
            },
            workflow=None
        )
    except Exception as e:
        logger.exception(f"Failed to record catfact_send_result: {e}")
    return entity

# Mock send_email function (assumed imported or defined elsewhere)
async def send_email(to_email: str, subject: str, body: str) -> bool:
    # TODO: replace with actual email service integration
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    await asyncio.sleep(0.1)
    return True