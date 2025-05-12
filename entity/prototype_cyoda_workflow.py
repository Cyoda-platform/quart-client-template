from dataclasses import dataclass
from typing import List, Optional, Dict
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

PET_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Guinea pigs communicate with squeaks and purrs.",
    "Goldfish can recognize their owners."
]

@dataclass
class PetQuery:
    type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    name: Optional[str] = None

@dataclass
class FavoriteAdd:
    petId: int

@dataclass
class EmptyBody:
    pass

async def fetch_pet_by_id(pet_id: int) -> Optional[Dict]:
    url = f"{PETSTORE_API_BASE}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"HTTP error fetching pet {pet_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching pet {pet_id}: {e}")
            return None

async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    status = filters.get("status", "available")
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status}

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []

    filtered = []
    type_filter = filters.get("type")
    tags_filter = set(t.lower() for t in (filters.get("tags") or []))
    name_filter = (filters.get("name") or "").lower()

    for pet in pets:
        pet_type = pet.get("category", {}).get("name")
        if type_filter and (not pet_type or pet_type.lower() != type_filter.lower()):
            continue

        if tags_filter:
            pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
            if not tags_filter.issubset(pet_tags):
                continue

        if name_filter and name_filter not in (pet.get("name") or "").lower():
            continue

        filtered.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet_type,
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", [])],
                "photoUrls": pet.get("photoUrls", []),
            }
        )
    return filtered

async def process_favorite(entity: Dict) -> Dict:
    pet_id = entity.get("id") or entity.get("petId")
    if not pet_id:
        logger.warning("No petId found in favorite entity for enrichment.")
        return entity

    pet_data = await fetch_pet_by_id(int(pet_id))
    if pet_data:
        entity["id"] = pet_data.get("id")
        entity["name"] = pet_data.get("name")
        entity["type"] = pet_data.get("category", {}).get("name")
        entity["status"] = pet_data.get("status")
        entity["tags"] = [tag.get("name") for tag in pet_data.get("tags", [])]
        entity["photoUrls"] = pet_data.get("photoUrls", [])
    else:
        logger.warning(f"Pet data not found for petId {pet_id}, favorite entity unchanged.")

    entity["added_at"] = datetime.utcnow().isoformat() + "Z"

    return entity

@app.route("/pets/query", methods=["POST"])
@validate_request(PetQuery)
async def pets_query(data: PetQuery):
    filters = data.__dict__
    pets = await fetch_pets_from_petstore(filters)
    return jsonify({"pets": pets})

@app.route("/favorites/add", methods=["POST"])
@validate_request(FavoriteAdd)
async def favorites_add(data: FavoriteAdd):
    pet_id = data.petId
    if not pet_id or not isinstance(pet_id, int):
        return jsonify({"success": False, "message": "Invalid or missing petId."}), 400

    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
    except Exception:
        pet = None

    if pet:
        logger.info(f"Pet {pet_id} already in favorites in entity_service")
        return jsonify({"success": True, "message": "Pet already in favorites."})

    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            entity={"id": pet_id},
            workflow=process_favorite
        )
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        logger.exception(f"Failed to add pet to favorites via entity_service: {e}")
        return jsonify({"success": False, "message": "Failed to add favorite."}), 500

@app.route("/favorites", methods=["GET"])
async def favorites_list():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION
        )
        return jsonify({"favorites": items})
    except Exception as e:
        logger.exception(f"Failed to get favorites from entity_service: {e}")
        return jsonify({"favorites": []})

@app.route("/fun/random-fact", methods=["POST"])
@validate_request(EmptyBody)
async def fun_random_fact(data: EmptyBody):
    import random
    fact = random.choice(PET_FACTS)
    return jsonify({"fact": fact})

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)