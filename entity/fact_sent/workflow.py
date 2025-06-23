import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fact_sent(entity: dict):
    # Orchestration of the workflow
    fact = entity.get("fact")
    if not fact:
        logger.error("process_fact_sent: no 'fact' in entity")
        return entity

    subscribers = await process_get_subscribers(entity)
    await process_send_emails(entity, subscribers, fact)
    await process_update_interactions(entity, len(subscribers))

    return entity

async def process_get_subscribers(entity: dict):
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        return subscribers
    except Exception as e:
        logger.exception(f"process_get_subscribers: error fetching subscribers: {e}")
        return []

async def process_send_emails(entity: dict, subscribers: list, fact: str):
    send_tasks = []
    subject = "Your Weekly Cat Fact \u001f\u007f"
    for subscriber in subscribers:
        email = subscriber.get("email")
        if email:
            send_tasks.append(send_email(email, subject, fact))
    if send_tasks:
        try:
            await asyncio.gather(*send_tasks)
        except Exception as e:
            logger.exception(f"process_send_emails: error sending emails: {e}")

async def process_update_interactions(entity: dict, sent_count: int):
    try:
        interactions = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=INTERACTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        if interactions:
            interaction = interactions[0]
            # Update interaction counts directly in entity attribute
            # Assuming entity has a nested 'interactions' dict attribute to hold this state
            if "interactions" not in entity:
                entity["interactions"] = {}
            entity["interactions"]["emails_sent"] = interaction.get("emails_sent", 0) + sent_count
            entity["interactions"]["opens"] = interaction.get("opens", 0)
            entity["interactions"]["clicks"] = interaction.get("clicks", 0)
        else:
            if "interactions" not in entity:
                entity["interactions"] = {}
            entity["interactions"]["emails_sent"] = sent_count
            entity["interactions"]["opens"] = 0
            entity["interactions"]["clicks"] = 0
    except Exception as e:
        logger.exception(f"process_update_interactions: error updating interactions: {e}")