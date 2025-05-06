import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"


async def process_fetch_cat_fact(entity: dict) -> None:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.warning("Cat fact API returned no fact")
                entity["data"] = "No fact available"
            else:
                entity["data"] = fact
        except Exception as e:
            logger.exception("Failed to fetch cat fact: %s", e)
            entity["data"] = "Failed to fetch cat fact"


async def process_fetch_cat_image(entity: dict) -> None:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_IMAGE_API, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                url = data[0].get("url")
                if url:
                    entity["data"] = url
                    return
            logger.warning("Cat image API returned unexpected data format")
            entity["data"] = ""
        except Exception as e:
            logger.exception("Failed to fetch cat image: %s", e)
            entity["data"] = ""


async def process_set_greeting(entity: dict) -> None:
    entity["data"] = None
