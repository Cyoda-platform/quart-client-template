import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

THECATAPI_KEY = ""  # Optional but recommended to avoid rate limits
THECATAPI_BASE = "https://api.thecatapi.com/v1"


async def process_fetch_images(entity: Dict[str, Any]) -> List[Dict[str, Any]]:
    breed_id = entity.get("breed_id")
    limit = entity.get("limit", 5)
    params = {"limit": limit}
    if breed_id:
        params["breed_id"] = breed_id
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if THECATAPI_KEY:
                headers["x-api-key"] = THECATAPI_KEY
            r = await client.get(f"{THECATAPI_BASE}/images/search", headers=headers, params=params, timeout=10)
            r.raise_for_status()
            images = r.json()
            result = []
            for img in images:
                breed_ids = [b.get("id") for b in img.get("breeds", [])] if img.get("breeds") else []
                result.append(
                    {
                        "id": img.get("id"),
                        "url": img.get("url"),
                        "breed_id": breed_ids[0] if breed_ids else None,
                    }
                )
            return result
    except Exception as e:
        logger.exception(e)
        return []