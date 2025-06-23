import asyncio
import logging
import uuid
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CAT_FACT_API_URL = "https://catfact.ninja/fact"

async def process_fetch_and_send_fact(entity: dict) -> dict:
    try:
        fact_data = await fetch_cat_fact()
        fact_text = fact_data.get("fact", "No fact retrieved")
        fact_id = str(uuid.uuid4())
        entity["factId"] = fact_id
        entity["fact"] = fact_text
        entity["createdAt"] = datetime.utcnow().isoformat()
        entity["sentCount"] = 0

        # Simulate sending emails to subscribers stored inside entity
        subscribers = entity.get("subscribers", {})
        for sub_id, sub in subscribers.items():
            try:
                await send_email(sub["email"], "Your Weekly Cat Fact 🐱", fact_text)
                entity["sentCount"] += 1
            except Exception as e:
                logger.exception(f"Failed to send email to {sub['email']}: {e}")

        entity["status"] = "completed"
    except Exception as e:
        logger.exception(f"Error in fetch_and_send_fact: {e}")
        entity["status"] = "failed"
        entity["error"] = str(e)
    return entity

async def process_subscribe(entity: dict) -> dict:
    email = entity.get("email")
    name = entity.get("name")
    if not email:
        entity["status"] = "failed"
        entity["error"] = "Email is required"
        return entity
    subscribers = entity.setdefault("subscribers", {})
    # Check if already subscribed
    for sub in subscribers.values():
        if sub.get("email", "").lower() == email.lower():
            entity["status"] = "exists"
            return entity
    subscriber_id = str(uuid.uuid4())
    subscribers[subscriber_id] = {"email": email, "name": name}
    entity["subscriberId"] = subscriber_id
    entity["status"] = "subscribed"
    return entity

async def process_record_interaction(entity: dict) -> dict:
    subscriber_id = entity.get("subscriberId")
    interaction_type = entity.get("interactionType")
    fact_id = entity.get("factId")

    subscribers = entity.get("subscribers", {})
    cat_facts = entity.get("cat_facts", {})

    if subscriber_id not in subscribers:
        entity["status"] = "failed"
        entity["error"] = "Subscriber not found"
        return entity
    if fact_id not in cat_facts:
        entity["status"] = "failed"
        entity["error"] = "Fact not found"
        return entity
    if interaction_type not in ("open", "click"):
        entity["status"] = "failed"
        entity["error"] = "Invalid interactionType"
        return entity

    interactions = entity.setdefault("interactions", [])
    interactions.append({
        "subscriberId": subscriber_id,
        "interactionType": interaction_type,
        "factId": fact_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    entity["status"] = "recorded"
    return entity

async def process_interaction(entity: dict) -> dict:
    # Workflow orchestration: route to appropriate processor by action type in entity
    action = entity.get("action")
    if action == "subscribe":
        return await process_subscribe(entity)
    elif action == "fetch_and_send_fact":
        return await process_fetch_and_send_fact(entity)
    elif action == "record_interaction":
        return await process_record_interaction(entity)
    else:
        entity["status"] = "unknown_action"
        return entity

async def fetch_cat_fact() -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(CAT_FACT_API_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()

async def send_email(to_email: str, subject: str, body: str):
    # TODO: implement real email sending
    logger.info(f"Mock send email to {to_email} subject '{subject}' body '{body}'")