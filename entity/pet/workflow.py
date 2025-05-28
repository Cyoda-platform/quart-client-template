import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

async def process_pet(entity: Dict) -> None:
    # workflow orchestration only
    if entity.get("action") == "fetch":
        await process_fetch(entity)
    elif entity.get("action") == "adopt":
        await process_adopt(entity)
    elif entity.get("action") == "finalize":
        await process_finalize(entity)
    entity['processed_at'] = datetime.utcnow().isoformat()

async def process_fetch(entity: Dict) -> None:
    # business logic for fetching pets from external API
    status = entity.get("status")
    tags = entity.get("tags")
    async with httpx.AsyncClient() as client:
        try:
            url = "https://petstore3.swagger.io/api/v3/pet/findByStatus"
            params = {"status": status} if status else {"status": "available,pending,sold"}
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            raw_pets = response.json()
            filtered = filter_pets(raw_pets, None, tags)
            processed = process_petstore_pets(filtered)
            entity['pets'] = processed
            entity['count'] = len(processed)
            entity['status'] = "fetched"
        except Exception as e:
            logging.getLogger(__name__).exception(e)
            entity['status'] = "error"
            entity['error'] = str(e)

async def process_adopt(entity: Dict) -> None:
    # business logic to process adoption request
    # just mark as submitted with timestamp
    entity['status'] = "adoption_submitted"
    entity['submitted_at'] = datetime.utcnow().isoformat()

async def process_finalize(entity: Dict) -> None:
    # placeholder for any finalization logic
    entity['status'] = "finalized"
    entity['finalized_at'] = datetime.utcnow().isoformat()

def filter_pets(pets: List[Dict], status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    filtered = pets
    if status:
        filtered = [p for p in filtered if p.get("status") == status]
    if tags:
        filtered = [p for p in filtered if "tags" in p and any(tag["name"] in tags for tag in p["tags"])]
    return filtered

def process_petstore_pets(raw_pets: List[Dict]) -> List[Dict]:
    processed = []
    for pet in raw_pets:
        processed.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "status": pet.get("status"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        })
    return processed