import logging
from datetime import datetime
import uuid
import asyncio
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_cat_fact(entity: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://catfact.ninja/fact", timeout=10)
            response.raise_for_status()
            data = response.json()
            fact = data.get("fact")
            if fact:
                entity.setdefault("result", {}).setdefault("content", {}).setdefault("catData", {})["fact"] = fact
        except Exception:
            logger.exception("Failed to fetch cat fact")

async def fetch_cat_image(entity: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://api.thecatapi.com/v1/images/search", timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                image_url = data[0].get("url")
                if image_url:
                    entity.setdefault("result", {}).setdefault("content", {}).setdefault("catData", {})["imageUrl"] = image_url
        except Exception:
            logger.exception("Failed to fetch cat image")

async def process_prepare_entity(entity: dict):
    if "resultId" not in entity or not entity["resultId"]:
        entity["resultId"] = str(uuid.uuid4())
    entity["status"] = "processing"
    entity["result"] = {
        "resultId": entity["resultId"],
        "content": {
            "helloWorldMessage": "Hello World",
            "catData": {}
        },
        "timestamp": None
    }
    entity["workflow_processedAt"] = None

async def process_finalize_entity(entity: dict, success: bool):
    entity["workflow_processedAt"] = datetime.utcnow().isoformat() + "Z"
    if success:
        entity["status"] = "completed"
        entity["result"]["timestamp"] = entity["workflow_processedAt"]
    else:
        entity["status"] = "failed"
        entity["result"] = {
            "error": "Failed to process request."
        }