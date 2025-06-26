import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_subscriber(entity: dict):
    # Workflow orchestration only
    if 'subscribedAt' not in entity:
        await process_add_subscription_timestamp(entity)
    cat_fact = await process_fetch_cat_fact()
    if cat_fact:
        await process_send_cat_fact_email(entity, cat_fact)
        await process_update_caches(cat_fact)
    await process_update_subscriber_count_cache()

async def process_add_subscription_timestamp(entity: dict):
    entity['subscribedAt'] = datetime.now(timezone.utc).isoformat()

async def process_fetch_cat_fact() -> str | None:
    try:
        return await fetch_cat_fact()
    except Exception:
        logger.exception("Failed to fetch cat fact")
        return None

async def process_send_cat_fact_email(entity: dict, cat_fact: str):
    await send_email(entity['email'], cat_fact)

async def process_update_caches(cat_fact: str):
    try:
        await cache.update_latest_fact(cat_fact)
    except Exception as e:
        logger.error(f"Failed to update latest fact and report cache: {e}")

async def process_update_subscriber_count_cache():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        await cache.update_subscriber_count(len(items))
    except Exception as e:
        logger.error(f"Failed to update subscriber count in cache: {e}")