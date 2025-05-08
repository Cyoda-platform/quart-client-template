import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CATFACTS_BASE = "https://catfact.ninja"


async def fetch_cat_facts(count: int) -> List[str]:
    facts = []
    try:
        async with httpx.AsyncClient() as client:
            limit = min(count, 500)
            r = await client.get(f"{CATFACTS_BASE}/facts?limit={limit}", timeout=10)
            r.raise_for_status()
            data = r.json()
            facts = [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception("Error fetching cat facts: %s", e)
    return facts