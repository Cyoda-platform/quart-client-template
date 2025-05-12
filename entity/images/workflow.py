import httpx
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

THE_CAT_API_BASE = "https://api.thecatapi.com/v1"
THE_CAT_API_HEADERS = {
    # "x-api-key": "YOUR_API_KEY"  # TODO: Add API key if needed
}

async def process_images(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    await process_fetch_image(entity)
    await process_finalize(entity)
    return entity

async def process_fetch_image(entity: Dict[str, Any]) -> None:
    idx = 0
    try:
        idx = int(entity['id'].split('_')[-1])
    except Exception:
        idx = 0
    url = f"{THE_CAT_API_BASE}/images/search?limit=1&page={idx}&order=Desc"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=THE_CAT_API_HEADERS, timeout=10)
            resp.raise_for_status()
            items = resp.json()
            if items:
                entity["content"] = items[0]["url"]
            else:
                entity["content"] = None
    except Exception as e:
        entity["content"] = None
        logger.exception(f"Failed to fetch image in workflow: {e}")

async def process_finalize(entity: Dict[str, Any]) -> None:
    entity["processedAt"] = datetime.utcnow().isoformat()