from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_external_data(entity: dict):
    """
    Fetch external data and store in entity['externalData'] or set failure.
    """
    input_data = entity.get("inputData", {})
    post_id = str(input_data.get("postId", "1"))
    external_data = await fetch_external_data(post_id)
    if not external_data:
        entity["status"] = "failed"
        entity["message"] = "Failed to retrieve external data"
        entity["result"] = None
        return
    entity["externalData"] = external_data

async def process_calculate_word_count(entity: dict):
    """
    Calculate word count from externalData and store in entity['result'].
    """
    external_data = entity.get("externalData", {})
    title = external_data.get("title", "")
    body = external_data.get("body", "")
    word_count = len((title + " " + body).split())

    entity["result"] = {
        "externalData": external_data,
        "wordCount": word_count,
    }

async def process_store_raw_data(entity: dict, entity_service, cyoda_token, ENTITY_VERSION):
    """
    Store supplementary raw data entity, separate from current entity.
    """
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_raw_data",
            entity_version=ENTITY_VERSION,
            entity={
                "jobId": entity.get("technical_id"),
                "rawData": entity.get("externalData"),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to add supplementary entity_raw_data: {e}")

async def fetch_external_data(some_param: str) -> dict:
    """
    External API call example.
    """
    url = f"https://jsonplaceholder.typicode.com/posts/{some_param}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch external data: {e}")
            return {}