import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_add_subscription_timestamp(entity: dict):
    entity['subscribedAt'] = datetime.now(timezone.utc).isoformat()
    entity["workflowProcessed"] = True

async def process_fetch_cat_fact(entity: dict):
    try:
        cat_fact = await fetch_cat_fact()
        entity["cat_fact"] = cat_fact
    except Exception:
        logger.exception("Failed to fetch cat fact")
        entity["cat_fact"] = None
    entity["workflowProcessed"] = True

async def process_send_cat_fact_email(entity: dict):
    cat_fact = entity.get("cat_fact")
    if cat_fact and 'email' in entity:
        try:
            await send_email(entity['email'], cat_fact)
        except Exception:
            logger.exception("Failed to send cat fact email")
    entity["workflowProcessed"] = True

async def process_update_caches(entity: dict):
    cat_fact = entity.get("cat_fact")
    if cat_fact:
        try:
            await cache.update_latest_fact(cat_fact)
        except Exception as e:
            logger.error(f"Failed to update latest fact and report cache: {e}")
    entity["workflowProcessed"] = True

async def process_update_subscriber_count_cache(entity: dict):
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        await cache.update_subscriber_count(len(items))
    except Exception as e:
        logger.error(f"Failed to update subscriber count in cache: {e}")
    entity["workflowProcessed"] = True

async def cat_fact_exists_condition(entity: dict) -> bool:
    return bool(entity.get("cat_fact"))

async def cat_fact_missing_condition(entity: dict) -> bool:
    return not entity.get("cat_fact")