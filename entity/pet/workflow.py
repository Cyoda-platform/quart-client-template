import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_fetch(entity: dict) -> None:
    # Fetch pets from external API and cache in entity
    pet_type = entity.get("type")
    status = entity.get("status")
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    params = {"status": status or "available"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            entity["pets"] = pets
    except Exception as e:
        logging.exception("Error fetching pets from Petstore API")
        entity["pets"] = []

async def process_matchmake(entity: dict) -> None:
    # Perform matchmaking logic calculating matchScore for each pet
    preferred_type = entity.get("preferredType")
    preferred_status = entity.get("preferredStatus")
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    params = {"status": preferred_status or "available"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            matched_pets = []
            for pet in pets:
                score = 0.0
                if preferred_type and pet.get("category", {}).get("name", "").lower() == preferred_type.lower():
                    score += 0.6
                if preferred_status and pet.get("status", "").lower() == preferred_status.lower():
                    score += 0.4
                if score > 0:
                    p = pet.copy()
                    p["matchScore"] = round(score, 2)
                    matched_pets.append(p)
            entity["matchedPets"] = matched_pets
    except Exception as e:
        logging.exception("Error during matchmaking")
        entity["matchedPets"] = []

async def process_description(entity: dict) -> None:
    # Add processedAt timestamp and description if missing
    entity['processedAt'] = datetime.utcnow().isoformat()
    if "description" not in entity or not entity["description"]:
        name = entity.get("name", "this pet")
        category = entity.get("category", {}).get("name", "pet")
        entity["description"] = f"Meet {name}! A lovely {category} waiting for a new home."

async def process_pet(entity: dict) -> None:
    # Workflow orchestration only: call other processing functions based on entity state
    if entity.get("action") == "fetch":
        await process_fetch(entity)
    elif entity.get("action") == "matchmake":
        await process_matchmake(entity)
    else:
        # Default processing (e.g. enrich with description)
        await process_description(entity)