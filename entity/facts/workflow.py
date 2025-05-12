import httpx
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

CAT_FACTS_API_BASE = "https://catfact.ninja"

async def process_facts(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    await process_fetch_fact(entity)
    await process_finalize(entity)
    return entity

async def process_fetch_fact(entity: Dict[str, Any]) -> None:
    idx = 0
    try:
        idx = int(entity['id'].split('_')[-1])
    except Exception:
        idx = 0
    url = f"{CAT_FACTS_API_BASE}/facts?limit=1&page={idx+1}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            facts = data.get("data", [])
            if facts:
                entity["content"] = facts[0]["fact"]
            else:
                entity["content"] = None
    except Exception as e:
        entity["content"] = None
        logger.exception(f"Failed to fetch fact in workflow: {e}")

async def process_finalize(entity: Dict[str, Any]) -> None:
    entity["wordCount"] = len(entity["content"].split()) if entity.get("content") else 0
    entity["processedAt"] = datetime.utcnow().isoformat()