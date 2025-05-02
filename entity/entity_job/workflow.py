from datetime import datetime
from typing import Dict

import httpx
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def process_set_created_at(entity: dict):
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat() + "Z"


async def process_validate_query(entity: dict):
    query = entity.get("query")
    if not query or not isinstance(query, str) or not query.strip():
        entity["status"] = "failed"
        entity["result"] = {"error": "Missing or invalid required field 'query'"}
        entity["processedAt"] = datetime.utcnow().isoformat() + "Z"
        return False
    return True


async def process_set_status_processing(entity: dict):
    entity["status"] = "processing"


async def process_fetch_external_data(entity: dict):
    query = entity.get("query").strip()
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json"}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            abstract = data.get("AbstractText", "")
            entity["externalData"] = {"abstract": abstract}
        except Exception as e:
            logger.exception(e)
            entity["externalData"] = {"error": str(e)}


async def process_update_status_and_result(entity: dict):
    external_data = entity.get("externalData", {})
    if "error" in external_data:
        entity["status"] = "failed"
        entity["result"] = {"error": external_data["error"]}
    else:
        entity["status"] = "completed"
        entity["result"] = {
            "query": entity.get("query"),
            "externalSummary": external_data.get("abstract", ""),
        }
    entity["processedAt"] = datetime.utcnow().isoformat() + "Z"
    entity.pop("externalData", None)