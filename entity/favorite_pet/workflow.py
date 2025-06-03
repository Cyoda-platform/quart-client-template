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

async def process_fetch_pets(entity: dict) -> dict:
    """
    Business logic to fetch pets from external Petstore API and filter by type/status.
    Modifies entity['pets'] with the resulting list.
    """
    type_filter = entity.get("type")
    status_filter = entity.get("status")
    statuses = [status_filter] if status_filter else ["available"]

    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        for status in statuses:
            try:
                resp = await client.get(
                    "https://petstore.swagger.io/v2/pet/findByStatus",
                    params={"status": status},
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
            except httpx.HTTPError as e:
                logging.getLogger(__name__).exception(f"Failed to fetch pets by status '{status}': {e}")

    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]

    entity["pets"] = pets
    return entity


async def process_cache_pets(entity: dict) -> dict:
    """
    Cache pets in entity state for retrieval.
    """
    # Assuming entity['pets'] contains the latest pets list
    # No external cache, just keep in entity['cached_pets']
    entity["cached_pets"] = entity.get("pets", [])
    return entity


async def process_mark_favorite(entity: dict) -> dict:
    """
    Mark the pet as favorite by storing petId in favorites list in entity.
    """
    pet_id = entity.get("petId")
    if pet_id is None:
        # No petId provided, nothing to do
        return entity

    favorites = entity.get("favorites", set())
    if not isinstance(favorites, set):
        favorites = set(favorites)
    favorites.add(pet_id)
    entity["favorites"] = favorites
    return entity


async def process_trigger_favorite_event(entity: dict) -> dict:
    """
    Fire and forget trigger event for pet_favorite action.
    """
    asyncio.create_task(trigger_event_workflow("pet_favorite", {"petId": entity.get("petId")}))
    return entity


async def process_trigger_query_event(entity: dict) -> dict:
    """
    Fire and forget trigger event for pet_query action.
    """
    asyncio.create_task(
        trigger_event_workflow(
            "pet_query",
            {
                "type": entity.get("type"),
                "status": entity.get("status"),
                "resultCount": len(entity.get("pets", [])),
            },
        )
    )
    return entity


async def process_favorite_pet(entity: dict) -> dict:
    # Workflow orchestration only, no business logic here
    await process_mark_favorite(entity)
    await process_trigger_favorite_event(entity)
    return entity