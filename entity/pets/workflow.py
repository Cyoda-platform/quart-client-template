import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_fetch(entity: Dict) -> None:
    # Fetch pets from external API and store in entity['pets']
    status = entity.get("status")
    category = entity.get("category")

    async with httpx.AsyncClient() as client:
        query_status = status if status else "available,pending,sold"
        url = "https://petstore.swagger.io/v2/pet/findByStatus"
        try:
            response = await client.get(url, params={"status": query_status})
            response.raise_for_status()
            pets = response.json()
            if category:
                cat_lower = category.lower()
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == cat_lower]
            entity["pets"] = pets
            entity["fetch_count"] = len(pets)
            entity["fetch_time"] = datetime.utcnow().isoformat()
        except Exception as e:
            entity["fetch_error"] = str(e)
            logging.getLogger(__name__).exception("Failed to fetch pets")

async def process_store(entity: Dict) -> None:
    # Store pets in entity for later retrieval
    # Normalize pets list for easy access
    pets = entity.get("pets", [])
    normalized_pets = []
    for pet in pets:
        pet_id = pet.get("id")
        if pet_id is not None:
            normalized_pets.append({
                "id": pet_id,
                "name": pet.get("name", ""),
                "category": pet.get("category", {}).get("name", ""),
                "status": pet.get("status", ""),
            })
    entity["stored_pets"] = normalized_pets
    entity["stored_count"] = len(normalized_pets)

async def process_filter(entity: Dict) -> None:
    # Filter stored pets by status and category if provided
    pets = entity.get("stored_pets", [])
    status = entity.get("filter_status")
    category = entity.get("filter_category")
    if status:
        sl = status.lower()
        pets = [p for p in pets if p["status"].lower() == sl]
    if category:
        cl = category.lower()
        pets = [p for p in pets if p["category"].lower() == cl]
    entity["filtered_pets"] = pets
    entity["filtered_count"] = len(pets)

async def process_adopt(entity: Dict) -> None:
    # Mark a pet as adopted (status = sold) in stored pets
    pet_id = entity.get("petId")
    if pet_id is None:
        entity["adopt_error"] = "petId not provided"
        return
    pets = entity.get("stored_pets", [])
    for pet in pets:
        if pet.get("id") == pet_id:
            pet["status"] = "sold"
            entity["adopted_pet"] = pet
            return
    entity["adopt_error"] = f"Pet with id {pet_id} not found"

async def process_pets(entity: Dict) -> Dict:
    # Workflow orchestration only - no business logic here
    action = entity.get("action")

    if action == "fetch":
        await process_fetch(entity)
        await process_store(entity)
    elif action == "get":
        await process_filter(entity)
    elif action == "adopt":
        await process_adopt(entity)

    # Common enrichments
    if "filtered_pets" in entity:
        pets_to_process = entity["filtered_pets"]
    elif "stored_pets" in entity:
        pets_to_process = entity["stored_pets"]
    elif "pets" in entity:
        pets_to_process = entity["pets"]
    else:
        pets_to_process = []

    # Normalize status field to lowercase if present
    for pet in pets_to_process:
        if "status" in pet and isinstance(pet["status"], str):
            pet["status"] = pet["status"].lower()
        # Add processed timestamp
        pet["processed_at"] = datetime.utcnow().isoformat()
        # Example enrichment: length of name
        if "name" in pet and isinstance(pet["name"], str):
            pet["name_length"] = len(pet["name"])

    return entity