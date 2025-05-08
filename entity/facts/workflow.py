import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

THECATAPI_KEY = ""  # Optional but recommended to avoid rate limits
THECATAPI_BASE = "https://api.thecatapi.com/v1"
CATFACTS_BASE = "https://catfact.ninja"


async def process_fetch_facts(entity: Dict[str, Any]) -> List[str]:
    count = entity.get("count", 5)
    try:
        async with httpx.AsyncClient() as client:
            limit = min(count, 500)
            r = await client.get(f"{CATFACTS_BASE}/facts?limit={limit}", timeout=10)
            r.raise_for_status()
            data = r.json()
            facts = [fact["fact"] for fact in data.get("data", [])]
            return facts
    except Exception as e:
        logger.exception(e)
        return []