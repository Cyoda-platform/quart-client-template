import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

async def process_capitalize_fact(entity: dict):
    fact_text = entity.get("fact", "")
    if fact_text:
        entity["fact"] = fact_text[0].upper() + fact_text[1:]

def process_set_created_at(entity: dict):
    entity.setdefault("created_at", datetime.utcnow().isoformat())