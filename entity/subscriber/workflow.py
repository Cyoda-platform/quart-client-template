import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

async def process_subscriber(entity: Dict) -> Dict:
    # Workflow orchestration only
    entity = await process_add_created_at(entity)
    entity = await process_normalize_email(entity)
    return entity

async def process_add_created_at(entity: Dict) -> Dict:
    # Add created_at timestamp if missing
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat() + "Z"
    return entity

async def process_normalize_email(entity: Dict) -> Dict:
    # Normalize email: strip whitespace and lowercase
    email = entity.get("email")
    if isinstance(email, str):
        entity["email"] = email.strip().lower()
    else:
        entity["email"] = ""
    return entity