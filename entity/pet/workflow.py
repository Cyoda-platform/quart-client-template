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

async def process_add_tags(entity: Dict):
    category_name = entity.get("category", {}).get("name", "").lower()
    tags = entity.get("tags", [])
    if category_name == "cat" and "purrfect" not in tags:
        tags.append("purrfect")
    elif category_name == "dog" and "woof-tastic" not in tags:
        tags.append("woof-tastic")
    elif category_name and "pet-tastic" not in tags:
        tags.append("pet-tastic")
    entity["tags"] = tags

async def process_add_processed_timestamp(entity: Dict):
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'

async def process_pet(entity: Dict) -> Dict:
    # Workflow orchestration only, call business logic functions
    await process_add_tags(entity)
    await process_add_processed_timestamp(entity)
    return entity