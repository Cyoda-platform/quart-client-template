import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_pet(entity: dict) -> dict:
    # Workflow orchestration only
    await process_fetch_and_cache_pets(entity)
    await process_favorite_pet(entity)
    await process_log_event(entity)
    return entity

async def process_fetch_and_cache_pets(entity: dict):
    # Business logic: fetch pets from external API and cache
    try:
        type_filter = entity.get("type")
        status_filter = entity.get("status")
        pets = await fetch_pets_from_petstore(type_filter, status_filter)
        entity["pets"] = pets
        entity["processedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logging.getLogger(__name__).exception("Error in process_fetch_and_cache_pets")

async def process_favorite_pet(entity: dict):
    # Business logic: mark pet as favorite if petId provided
    pet_id = entity.get("petId")
    if pet_id is not None:
        favorites = entity.setdefault("favorites", set())
        favorites.add(pet_id)
        entity["favoriteMarkedAt"] = datetime.utcnow().isoformat()

async def process_log_event(entity: dict):
    # Business logic: log event asynchronously
    event_type = entity.get("eventType", "generic_event")
    logger = logging.getLogger(__name__)
    logger.info(f"Event {event_type} processed for entity with id {entity.get('id', 'unknown')}")
    await asyncio.sleep(0)  # simulate async logging or event emission

async def fetch_pets_from_petstore(type_filter: Optional[str], status_filter: Optional[str]) -> List[dict]:
    statuses = [status_filter] if status_filter else ["available"]
    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        for status in statuses:
            try:
                resp = await client.get(
                    "https://petstore.swagger.io/v2/pet/findByStatus", params={"status": status}
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
            except httpx.HTTPError as e:
                logging.getLogger(__name__).exception(f"Failed to fetch pets by status '{status}': {e}")
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets