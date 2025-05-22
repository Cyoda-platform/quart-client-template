import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> list:
    PETSTORE_API_BASE = "https://petstore.swagger.io/v2"
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
    except Exception as e:
        logger.exception("Error fetching pets from Petstore API")
        return []

async def process_add_pet_entities(pets: list):
    for pet_data in pets:
        try:
            # TODO: Replace with real entity_service.add_item call
            # await entity_service.add_item(token=cyoda_auth_service, entity_model="pet", entity_version=ENTITY_VERSION, entity=pet_data, workflow=process_pet)
            pass
        except Exception:
            logger.exception("Failed to add pet entity in pet_fetch_job workflow")

async def process_pet_fetch_job(entity: dict) -> None:
    # Workflow orchestration only
    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()
    pet_type = entity.get("type")
    status = entity.get("status")
    try:
        pets = await fetch_pets_from_petstore(pet_type, status)
        await process_add_pet_entities(pets)
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result"] = {"count": len(pets)}
    except Exception as e:
        logger.exception("Failed processing pet_fetch_job")
        entity["status"] = "failed"
        entity["error"] = str(e)