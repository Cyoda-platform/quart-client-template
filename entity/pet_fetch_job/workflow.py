import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> list:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            params = {}
            if status:
                params["status"] = status
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

async def process_add_pet(pet_entity: dict):
    # TODO: Implement logic to add pet entity (e.g., create or update in DB)
    # Here just a placeholder for business logic
    pass

async def process_update_job_success(entity: dict, pets_count: int):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()
    entity["count"] = pets_count

async def process_update_job_failure(entity: dict, error_msg: str):
    entity["status"] = "failed"
    entity["error"] = error_msg

async def process_pet_fetch_job(entity: dict) -> dict:
    job_id = entity.get("id")
    type_ = entity.get("type")
    status_filter = entity.get("statusFilter")

    logger.info(f"Workflow process_pet_fetch_job: Starting fetch job {job_id} with type={type_} status={status_filter}")

    try:
        pets = await fetch_pets_from_petstore(type_, status_filter)
        logger.info(f"Fetched {len(pets)} pets from external API for job {job_id}")

        for pet in pets:
            pet_data = pet.copy()
            pet_data.pop("id", None)
            await process_add_pet(pet_data)

        await process_update_job_success(entity, len(pets))
        logger.info(f"Fetch job {job_id} completed successfully")
    except Exception as e:
        logger.exception(f"Fetch job {job_id} failed: {e}")
        try:
            await process_update_job_failure(entity, str(e))
        except Exception as inner_e:
            logger.exception(f"Failed to update failed job status for job {job_id}: {inner_e}")

    return entity