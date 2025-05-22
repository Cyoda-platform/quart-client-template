import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_fetch_and_sync(entity: Dict) -> None:
    """Fetch pets from external API and sync into entity."""
    async with httpx.AsyncClient() as client:
        params = {}
        if 'filter' in entity and entity['filter'].get('status'):
            params['status'] = entity['filter']['status']
        r = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params=params)
        r.raise_for_status()
        pets_raw = r.json()

    pets_transformed = []
    for pet in pets_raw:
        pet_id = pet.get("id")
        name = pet.get("name", "")
        category = pet.get("category") or {}
        status = pet.get("status", "available")
        tags = [tag.get("name") for tag in pet.get("tags", []) if "name" in tag]
        if category.get("name", "").lower() == "cat":
            tags.append("purrfect")
        elif category.get("name", "").lower() == "dog":
            tags.append("woof-tastic")
        else:
            tags.append("pet-tastic")
        pets_transformed.append({
            "id": pet_id,
            "name": name,
            "category": category,
            "status": status,
            "tags": tags,
        })
    entity['pets'] = pets_transformed

async def process_search(entity: Dict) -> None:
    """Search cached pets based on filters in entity."""
    pets = entity.get('pets', [])
    name = entity.get('name')
    status_filter = entity.get('status')
    if isinstance(status_filter, str):
        status_filter = [status_filter]
    category = entity.get('category')

    results = pets
    if name:
        results = [p for p in results if name.lower() in p.get("name", "").lower()]
    if status_filter:
        results = [p for p in results if p.get("status") in status_filter]
    if category:
        results = [p for p in results if p.get("category", {}).get("name", "").lower() == category.lower()]

    entity['results'] = results

async def process_adoption(entity: Dict) -> None:
    """Orchestrate adoption workflow without business logic."""
    # Workflow orchestration only - call business logic processors
    await process_validate_adoption(entity)
    await process_mark_adopted(entity)
    await process_record_adoption(entity)
    await process_finalize_adoption(entity)

async def process_validate_adoption(entity: Dict) -> None:
    """Validate adoption request."""
    pet = entity.get('pet')
    if not pet:
        entity['error'] = "Pet not found"
        return
    if pet.get('status') != 'available':
        entity['error'] = f"Sorry, {pet.get('name')} is not available for adoption."

async def process_mark_adopted(entity: Dict) -> None:
    """Mark pet as adopted in entity state."""
    if entity.get('error'):
        return
    pet = entity.get('pet')
    pet['status'] = 'adopted'

async def process_record_adoption(entity: Dict) -> None:
    """Record adoption details."""
    if entity.get('error'):
        return
    adopter = entity.get('adopter')
    pet = entity.get('pet')
    adopted_at = datetime.utcnow().isoformat() + 'Z'
    entity['adopted_at'] = adopted_at
    # Store adoption info inside entity for persistence or further processing
    entity['adoption_record'] = {
        "adopter_email": adopter.get('email') if adopter else None,
        "pet_id": pet.get('id') if pet else None,
        "adopted_at": adopted_at,
    }

async def process_finalize_adoption(entity: Dict) -> None:
    """Prepare final adoption response message."""
    if entity.get('error'):
        entity['success'] = False
        entity['message'] = entity['error']
    else:
        adopter_name = entity.get('adopter', {}).get('name', 'Adopter')
        pet_name = entity.get('pet', {}).get('name', 'pet')
        entity['success'] = True
        entity['message'] = f"Congrats {adopter_name}! You adopted {pet_name}."
```