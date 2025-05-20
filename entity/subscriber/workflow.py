import asyncio
from datetime import datetime
import logging

async def process_subscriber(entity: dict) -> dict:
    # Workflow orchestration only - call business logic functions in order

    # 1. Ensure subscription timestamp is set
    await process_set_subscribed_at(entity)

    # 2. Fetch cat fact if needed
    if entity.get("needs_fact_fetch", False):
        await process_fetch_cat_fact(entity)

    # 3. Send cat fact emails if ready
    if entity.get("fact_fetched", False) and not entity.get("emails_sent", False):
        await process_send_emails(entity)

    # 4. Update reporting stats
    await process_update_reporting(entity)

    return entity

async def process_set_subscribed_at(entity: dict):
    if "subscribedAt" not in entity:
        entity["subscribedAt"] = datetime.utcnow().isoformat()

async def process_fetch_cat_fact(entity: dict):
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://catfact.ninja/fact", timeout=10)
            resp.raise_for_status()
            fact_data = resp.json()
            fact = fact_data.get("fact")
            if fact:
                entity["catFact"] = fact
                entity["fact_fetched"] = True
                entity["factFetchedAt"] = datetime.utcnow().isoformat()
            else:
                entity["fact_fetched"] = False
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        entity["fact_fetched"] = False

async def process_send_emails(entity: dict):
    # TODO: Replace with real email sending logic
    # Simulate sending emails with async sleep
    await asyncio.sleep(0.5)
    entity["emails_sent"] = True
    entity["emailsSentAt"] = datetime.utcnow().isoformat()

async def process_update_reporting(entity: dict):
    # Update reporting stats in the entity
    entity.setdefault("reporting", {})
    reporting = entity["reporting"]
    reporting["lastUpdatedAt"] = datetime.utcnow().isoformat()
    # Increment sent count if emails_sent is True
    if entity.get("emails_sent", False):
        reporting["emailsSentCount"] = reporting.get("emailsSentCount", 0) + 1