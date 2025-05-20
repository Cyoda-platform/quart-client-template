import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Signup:
    email: str

entity_name = "subscriber"  # underscore lowercase entity name

async def process_validate_email(entity: Dict) -> None:
    email = entity.get("email", "")
    if not isinstance(email, str):
        raise ValueError("Email must be a string")
    email = email.strip().lower()
    if "@" not in email or not email:
        raise ValueError("Invalid email format")
    entity["email"] = email

async def process_check_duplicate(entity: Dict) -> None:
    email = entity["email"]
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.email",
                    "operatorType": "EQUALS",
                    "value": email,
                    "type": "simple"
                }
            ]
        }
    }
    existing = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    if existing:
        raise ValueError("Subscriber already exists")

async def process_add_timestamps(entity: Dict) -> None:
    entity["createdAt"] = datetime.utcnow().isoformat()

async def process_subscriber(entity: Dict) -> None:
    # Workflow orchestration only - no business logic here
    await process_validate_email(entity)
    await process_check_duplicate(entity)
    await process_add_timestamps(entity)