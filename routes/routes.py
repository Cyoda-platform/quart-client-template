from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class PetFetchRequest:
    category: Optional[str]
    status: Optional[str]

@dataclass
class PetFilter:
    category: Optional[str]
    status: Optional[str]

@dataclass
class PetFilterRequest:
    filter: PetFilter
    sort_by: Optional[str]

FUN_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Parrots will selflessly help each other.",
    "Guinea pigs communicate with squeaks and purrs."
]

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(category: Optional[str], status: Optional[str]) -> List[Dict]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching from Petstore API: {e}")
            return []
    if category:
        return [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == category.lower()]
    return pets

async def process_fetch_pets(entity: Dict[str, Any]) -> None:
    # Fetch pets from external API based on the entity's category and status fields
    category = entity.get("category")
    status = entity.get("status")
    pets = await fetch_pets_from_petstore(category, status)
    # Add each pet as a separate entity with the pet workflow
    for pet in pets:
        try:
            # Add pet entity, triggers process_pet workflow
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet
            )
        except Exception as e:
            logger.exception(f"Error adding pet entity: {e}")
    # Mark fetch_pets entity as processed with timestamp
    entity["fetched_at"] = datetime.utcnow().isoformat() + "Z"

async def process_pet(entity: Dict[str, Any]) -> None:
    # Enrich pet entity with a fun fact and processed timestamp
    import random
    entity["fun_fact"] = random.choice(FUN_FACTS)
    entity["processed_timestamp"] = datetime.utcnow().isoformat() + "Z"

@routes_bp.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)
async def pets_fetch(data: PetFetchRequest):
    # Add a 'fetch_pets' entity that triggers the workflow to fetch and add pets asynchronously
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="fetch_pets",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__
        )
        return jsonify({"message": "Fetch request accepted and processing started."}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate fetch."}), 500

@routes_bp.route("/pets", methods=["GET"])
async def pets_get():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        items = []
    return jsonify({"pets": items})

@routes_bp.route("/pets/filter", methods=["POST"])
@validate_request(PetFilterRequest)
async def pets_filter(data: PetFilterRequest):
    filter_criteria = data.filter.__dict__
    sort_by = data.sort_by
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": []
        }
    }
    for key, val in filter_criteria.items():
        if val is not None:
            if key == "category":
                condition["cyoda"]["conditions"].append({
                    "jsonPath": "$.category.name",
                    "operatorType": "IEQUALS",
                    "value": val,
                    "type": "simple"
                })
            else:
                condition["cyoda"]["conditions"].append({
                    "jsonPath": f"$.{key}",
                    "operatorType": "IEQUALS",
                    "value": val,
                    "type": "simple"
                })
    try:
        if condition["cyoda"]["conditions"]:
            pets = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            pets = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
            )
    except Exception as e:
        logger.exception(e)
        pets = []
    if sort_by:
        key_func = None
        if sort_by == "name":
            key_func = lambda p: p.get("name", "").lower()
        elif sort_by == "category":
            key_func = lambda p: p.get("category", {}).get("name", "").lower()
        if key_func:
            try:
                pets = sorted(pets, key=key_func)
            except Exception as e:
                logger.exception(f"Error sorting pets: {e}")
    return jsonify({"pets": pets})