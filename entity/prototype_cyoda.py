from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

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

def add_fun_fact_to_pet(pet: Dict) -> Dict:
    import random
    pet_copy = pet.copy()
    pet_copy["fun_fact"] = random.choice(FUN_FACTS)
    return pet_copy

async def process_fetch_pets(data: Dict[str, Any]) -> None:
    category = data.get("category")
    status = data.get("status")
    pets = await fetch_pets_from_petstore(category, status)
    enriched = [add_fun_fact_to_pet(p) for p in pets]
    # Save each enriched pet to entity_service
    for pet in enriched:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet
            )
        except Exception as e:
            logger.exception(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)
async def pets_fetch(data: PetFetchRequest):
    await process_fetch_pets(data.__dict__)
    return jsonify({"message": "Pets data fetched and processed."}), 202

@app.route("/pets", methods=["GET"])
async def pets_get():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        pets = []
    return jsonify({"pets": pets})

@app.route("/pets/filter", methods=["POST"])
@validate_request(PetFilterRequest)
async def pets_filter(data: PetFilterRequest):
    crit = data.filter
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": []
        }
    }
    if crit.category:
        condition["cyoda"]["conditions"].append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": crit.category,
            "type": "simple"
        })
    if crit.status:
        condition["cyoda"]["conditions"].append({
            "jsonPath": "$.status",
            "operatorType": "IEQUALS",
            "value": crit.status,
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
    if data.sort_by:
        key = None
        if data.sort_by == "name":
            key = lambda p: p.get("name", "").lower()
        elif data.sort_by == "category":
            key = lambda p: p.get("category", {}).get("name", "").lower()
        if key:
            pets = sorted(pets, key=key)
    return jsonify({"pets": pets})

if __name__ == '__main__':
    import sys
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(fmt)
    logger.addHandler(console)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)