import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

async def process_fetch_metadata(entity: dict):
    url = entity.get("url")
    if url:
        try:
            async with httpx.AsyncClient() as client:
                head_resp = await client.head(url, timeout=5)
                if head_resp.status_code == 200:
                    entity["content_type"] = head_resp.headers.get("Content-Type", "")
                    content_length = head_resp.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        entity["content_length"] = int(content_length)
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for image: {e}")

def process_add_processed_at(entity: dict):
    entity["processed_at"] = datetime.utcnow().isoformat()