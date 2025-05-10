import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

async def process_fetch_facts() -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CAT_FACTS_API, params={"limit": 5})
            resp.raise_for_status()
            data = resp.json()
            return [fact["fact"] for fact in data.get("data", [])]
    except Exception:
        logger.exception("Failed to fetch cat facts")
        return []

async def process_fetch_breeds(filter_breed: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CAT_BREEDS_API)
            resp.raise_for_status()
            breeds = resp.json()
            if filter_breed:
                breeds = [b for b in breeds if filter_breed.lower() in b.get("name", "").lower()]
            return [
                {
                    "name": b.get("name"),
                    "origin": b.get("origin"),
                    "description": b.get("description")
                }
                for b in breeds
            ]
    except Exception:
        logger.exception("Failed to fetch cat breeds")
        return []

async def process_fetch_images() -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CAT_IMAGES_API, params={"limit": 5})
            resp.raise_for_status()
            images = resp.json()
            return [img.get("url") for img in images if img.get("url")]
    except Exception:
        logger.exception("Failed to fetch cat images")
        return []