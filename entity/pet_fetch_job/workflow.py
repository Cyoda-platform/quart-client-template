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

async def process_add_pet(entity: dict):
    pets_to_add = entity.setdefault("pets_to_add", [])
    if pets_to_add:
        pet = pets_to_add.pop(0)
        # Simulate adding pet (e.g., to DB)
        added_pets = entity.setdefault("added_pets", [])
        added_pets.append(pet)
        entity["pets_to_add"] = pets_to_add
    entity["workflowProcessed"] = True

async def process_update_job_success(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()
    entity["count"] = len(entity.get("added_pets", []))
    entity["workflowProcessed"] = True

async def process_update_job_failure(entity: dict):
    entity["status"] = "failed"
    entity["error"] = entity.get("error", "Fetch failed")
    entity["workflowProcessed"] = True

async def process_pet_fetch_job(entity: dict):
    job_id = entity.get("id")
    type_ = entity.get("type")
    status_filter = entity.get("statusFilter")

    logger.info(f"Workflow process_pet_fetch_job: Starting fetch job {job_id} with type={type_} status={status_filter}")

    try:
        pets = await fetch_pets_from_petstore(type_, status_filter)
        logger.info(f"Fetched {len(pets)} pets from external API for job {job_id}")
        entity["pets_to_add"] = []
        for pet in pets:
            pet_data = pet.copy()
            pet_data.pop("id", None)
            entity["pets_to_add"].append(pet_data)
        entity["added_pets"] = []
        entity["workflowProcessed"] = True
    except Exception as e:
        logger.exception(f"Fetch job {job_id} failed: {e}")
        entity["error"] = str(e)
        entity["workflowProcessed"] = True

async def fetch_failure_condition(entity: dict) -> bool:
    return entity.get("error") is not None

async def fetch_success_condition(entity: dict) -> bool:
    return entity.get("error") is None and "pets_to_add" in entity

async def has_more_pets_to_add(entity: dict) -> bool:
    pets_to_add = entity.get("pets_to_add", [])
    return len(pets_to_add) > 0

async def no_more_pets_to_add(entity: dict) -> bool:
    pets_to_add = entity.get("pets_to_add", [])
    return len(pets_to_add) == 0

async def process_update_job_failure(entity: dict):
    entity["status"] = "failed"
    entity["error"] = entity.get("error", "Unknown error")
    entity["workflowProcessed"] = True

async def process_update_job_success(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()
    entity["count"] = len(entity.get("added_pets", []))
    entity["workflowProcessed"] = True