import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"


async def process_fetch_cat_fact(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CAT_FACT_API)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact", "No fact found.")
            entity["fetched_cat_data"] = fact
    except Exception as e:
        logger.exception("Failed to fetch cat fact")
        entity["fetched_cat_data"] = "Failed to retrieve cat fact."


async def process_fetch_cat_image(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CAT_IMAGE_API)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                url = data[0].get("url", "No image URL found.")
                entity["fetched_cat_data"] = url
            else:
                entity["fetched_cat_data"] = "No image URL found."
    except Exception as e:
        logger.exception("Failed to fetch cat image")
        entity["fetched_cat_data"] = "Failed to retrieve cat image."


async def process_prepare_result(entity: dict):
    message = "Hello World"
    cat_data = entity.get("fetched_cat_data", None)
    entity["result"] = {
        "message": message,
        "catData": cat_data
    }


async def process_set_done_status(entity: dict):
    entity["status"] = "done"
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"


async def process_set_failed_status(entity: dict, error: Exception):
    entity["status"] = "failed"
    entity["error"] = str(error)
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"