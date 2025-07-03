from datetime import datetime
from typing import Dict, Any
import logging
import asyncio
import httpx

from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

book_cache: Dict[str, Dict[str, Any]] = {}
search_count: Dict[str, int] = {}

OPEN_LIBRARY_WORKS_API = "https://openlibrary.org{work_key}.json"

async def fetch_work_description(work_key: str) -> str:
    url = OPEN_LIBRARY_WORKS_API.format(work_key=work_key)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            desc = data.get("description")
            if isinstance(desc, dict):
                return desc.get("value")
            elif isinstance(desc, str):
                return desc
        except Exception as e:
            logger.warning(f"Failed to fetch description for {work_key}: {e}")
            logger.exception(e)
    return None

async def condition_need_enrichment(entity: dict) -> bool:
    try:
        if "description" not in entity or entity.get("description") is None:
            return True
        processed_at = entity.get("processed_at")
        if not processed_at:
            return True
        # TODO: Add logic to check if processed_at is stale (e.g., older than 1 day)
        return False
    except Exception as e:
        logger.exception(e)
        return False

async def condition_no_enrichment_needed(entity: dict) -> bool:
    try:
        return not await condition_need_enrichment(entity)
    except Exception as e:
        logger.exception(e)
        return False

async def enrich_book(entity: dict):
    try:
        entity["processed_at"] = datetime.utcnow().isoformat()
        work_key = f"/works/{entity.get('book_id')}"
        description = await fetch_work_description(work_key)
        if description:
            entity["description"] = description
        # Genre enrichment or other enrichment can be added here
        logger.info(f"Enriched book {entity.get('book_id')}")
    except Exception as e:
        logger.exception(e)

async def update_cache(entity: dict):
    try:
        book_cache[entity["book_id"]] = entity
        if entity["book_id"] not in search_count:
            search_count[entity["book_id"]] = 0
        logger.info(f"Cache updated for book {entity.get('book_id')}")
    except Exception as e:
        logger.exception(e)