import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def process_fetch_cat_image(entity: dict):
    url = "https://api.thecatapi.com/v1/images/search"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data and "url" in data[0]:
                entity["data"] = data[0]["url"]
                entity["status"] = "completed"
            else:
                logger.warning("Unexpected response structure from cat image API")
                entity["data"] = ""
                entity["status"] = "failed"
        except Exception as e:
            logger.exception(f"Error fetching cat image: {e}")
            entity["data"] = ""
            entity["status"] = "failed"


async def process_fetch_cat_fact(entity: dict):
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact") if isinstance(data, dict) else None
            if fact:
                entity["data"] = fact
                entity["status"] = "completed"
            else:
                logger.warning("Unexpected response structure from cat fact API")
                entity["data"] = ""
                entity["status"] = "failed"
        except Exception as e:
            logger.exception(f"Error fetching cat fact: {e}")
            entity["data"] = ""
            entity["status"] = "failed"
