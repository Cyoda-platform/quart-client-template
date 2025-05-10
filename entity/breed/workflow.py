import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

async def enrich_breed_description(entity: dict):
    if "description" not in entity or not entity.get("description"):
        breed_id = entity.get("id")
        if breed_id:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{CAT_API_BASE}/breeds/{breed_id}")
                    resp.raise_for_status()
                    data = resp.json()
                    entity["name"] = data.get("name", entity.get("name"))
                    entity["origin"] = data.get("origin", entity.get("origin"))
                    entity["description"] = data.get("description", "")
            except Exception as e:
                logger.warning(f"Failed to enrich breed {breed_id}: {e}")

def add_processed_timestamp(entity: dict):
    entity["processed_at"] = datetime.utcnow().isoformat()