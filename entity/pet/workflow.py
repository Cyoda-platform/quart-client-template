import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pet_details_from_petstore(pet_id):
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            logger.exception(f"Error fetching pet details for id {pet_id}")
            return None

async def add_processed_timestamp(entity: dict):
    if "processed_at" not in entity:
        entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
    entity["workflowProcessed"] = True

async def enrich_description(entity: dict):
    if (not entity.get("description")) and entity.get("id"):
        pet_id = str(entity["id"])
        pet_details = await fetch_pet_details_from_petstore(pet_id)
        if pet_details and pet_details.get("description"):
            entity["description"] = pet_details["description"]
    entity["workflowProcessed"] = True

async def start_processing(entity: dict):
    await add_processed_timestamp(entity)

async def timestamp_added(entity: dict):
    await enrich_description(entity)

async def enrichment_done(entity: dict):
    entity["workflowProcessed"] = True

async def process_pet(entity: dict):
    try:
        await add_processed_timestamp(entity)
        await enrich_description(entity)
    except Exception:
        logger.exception("Exception in process_pet workflow")
    return entity