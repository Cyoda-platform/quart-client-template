import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"


async def process_fetch_pet_data(entity: dict):
    pet_id = entity.get("id")
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "id" not in data:
            raise ValueError("Invalid response structure: missing 'id'")
        entity["name"] = data.get("name")
        entity["category"] = data.get("category", {}).get("name") if data.get("category") else None
        entity["status"] = data.get("status")
        entity["photoUrls"] = data.get("photoUrls", [])


async def process_set_failed(entity: dict, error_message: str):
    entity["processingStatus"] = "failed"
    entity["processingError"] = error_message
    entity["processedAt"] = datetime.utcnow().isoformat()


async def process_set_processing(entity: dict):
    entity["processingStatus"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()


async def process_set_completed(entity: dict):
    entity["processingStatus"] = "completed"
    entity["processedAt"] = datetime.utcnow().isoformat()