import httpx
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

THE_CAT_API_BASE = "https://api.thecatapi.com/v1"
THE_CAT_API_HEADERS = {
    # "x-api-key": "YOUR_API_KEY"  # TODO: Add API key if needed
}

async def process_breeds(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow orchestration only
    await process_fetch_breed(entity)
    await process_finalize(entity)
    return entity

async def process_fetch_breed(entity: Dict[str, Any]) -> None:
    breed_id = entity.get('id')
    if not breed_id:
        entity["content"] = None
        entity["normalizedBreedName"] = ""
        entity["processedAt"] = datetime.utcnow().isoformat()
        return
    url = f"{THE_CAT_API_BASE}/breeds/{breed_id}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=THE_CAT_API_HEADERS, timeout=10)
            resp.raise_for_status()
            breed_data = resp.json()
            entity["content"] = breed_data
            entity["normalizedBreedName"] = breed_data.get("name", "").lower()
    except Exception as e:
        entity["content"] = None
        entity["normalizedBreedName"] = ""
        logger.exception(f"Failed to fetch breed in workflow: {e}")

async def process_finalize(entity: Dict[str, Any]) -> None:
    entity["processedAt"] = datetime.utcnow().isoformat()