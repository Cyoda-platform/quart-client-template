import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_cat_fact() -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://catfact.ninja/fact", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return data.get("fact", "")
    except Exception:
        logger.exception("Failed to fetch cat fact")
        return ""

async def process_created(entity: dict):
    event = entity.get("_event_meta", {}).get("original_event", {})
    timestamp = event.get("timestamp")
    try:
        datetime.fromisoformat(timestamp)
    except Exception:
        timestamp = datetime.utcnow().isoformat() + "Z"
    cat_fact = await fetch_cat_fact()
    entity.update({
        "order_id": event.get("order_id"),
        "cat_type": event.get("cat_type"),
        "quantity": event.get("quantity"),
        "price": event.get("price"),
        "status": "created",
        "last_updated": timestamp,
        "cat_fact": cat_fact,
    })

async def process_updated(entity: dict):
    event = entity.get("_event_meta", {}).get("original_event", {})
    timestamp = event.get("timestamp")
    try:
        datetime.fromisoformat(timestamp)
    except Exception:
        timestamp = datetime.utcnow().isoformat() + "Z"
    cat_fact = await fetch_cat_fact()
    entity.update({
        "cat_type": event.get("cat_type", entity.get("cat_type")),
        "quantity": event.get("quantity", entity.get("quantity")),
        "price": event.get("price", entity.get("price")),
        "status": "updated",
        "last_updated": timestamp,
        "cat_fact": cat_fact or entity.get("cat_fact"),
    })

async def process_canceled(entity: dict):
    event = entity.get("_event_meta", {}).get("original_event", {})
    timestamp = event.get("timestamp")
    try:
        datetime.fromisoformat(timestamp)
    except Exception:
        timestamp = datetime.utcnow().isoformat() + "Z"
    cat_fact = await fetch_cat_fact()
    entity.update({
        "status": "canceled",
        "last_updated": timestamp,
        "cat_fact": cat_fact or entity.get("cat_fact"),
    })

async def process_order(entity: dict) -> dict:
    event_meta = entity.pop("_event_meta", {})
    event_type = event_meta.get("event_type")
    if not event_type or not isinstance(event_meta.get("original_event"), dict):
        logger.warning("Workflow called without valid event metadata")
        return entity

    entity["processed_at"] = datetime.utcnow().isoformat() + "Z"

    if event_type == "created":
        await process_created(entity)
    elif event_type == "updated":
        await process_updated(entity)
    elif event_type == "canceled":
        await process_canceled(entity)
    else:
        logger.warning(f"Unknown event_type in workflow: {event_type}")

    return entity