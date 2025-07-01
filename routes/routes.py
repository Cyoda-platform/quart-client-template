from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

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

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

@dataclass
class SearchRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class PetIdRequest:
    petId: int

# Workflow function for pet_entity
async def process_pet_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    pet_id = entity.get("id")
    if pet_id is None:
        logger.warning("Pet entity missing 'id', skipping enrichment")
        return entity

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet_data = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch pet data for id {pet_id}: {e}")
            pet_data = None

    if pet_data:
        entity["name"] = pet_data.get("name", entity.get("name"))
        entity["type"] = pet_data.get("category", {}).get("name", entity.get("type"))
        entity["status"] = pet_data.get("status", entity.get("status"))
        entity["photoUrls"] = pet_data.get("photoUrls", entity.get("photoUrls", []))
        entity["last_enriched_at"] = datetime.utcnow().isoformat() + "Z"
    else:
        logger.info(f"No enrichment data for pet id {pet_id}")

    return entity

# Workflow function for favorite_entity
async def process_favorite_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    user_id = entity.get("user_id")
    pet_id = entity.get("pet_id")
    action = entity.get("action")

    if not user_id or not pet_id or action not in {"add", "remove"}:
        logger.warning("Invalid favorite_entity data, skipping processing")
        return entity

    favorite_entity_model = "favorite_record"
    favorite_entity_id = f"{user_id}_{pet_id}"

    if action == "add":
        try:
            existing = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=favorite_entity_model,
                entity_id=favorite_entity_id,
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.error(f"Failed to get favorite record: {e}")
            existing = None

        if not existing:
            fav_entity = {
                "id": favorite_entity_id,
                "user_id": user_id,
                "pet_id": pet_id,
                "added_at": datetime.utcnow().isoformat() + "Z",
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=favorite_entity_model,
                    entity_version=ENTITY_VERSION,
                    entity=fav_entity,
                    workflow=None,
                )
            except Exception as e:
                logger.error(f"Failed to add favorite record: {e}")
    elif action == "remove":
        try:
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model=favorite_entity_model,
                entity_id=favorite_entity_id,
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.warning(f"Failed to delete favorite record {favorite_entity_id}: {e}")

    try:
        favorites_list = await entity_service.search_items(
            token=cyoda_auth_service,
            entity_model=favorite_entity_model,
            entity_version=ENTITY_VERSION,
            filters={"user_id": user_id},
        )
        favorite_count = len(favorites_list)
    except Exception as e:
        logger.error(f"Failed to count favorites for user {user_id}: {e}")
        favorite_count = 0

    entity["favoriteCount"] = favorite_count

    return entity

# Workflow function for pet_search_request entity
async def process_pet_search_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    pet_type = entity.get("type")
    status = entity.get("status", "available")

    params = {"status": status}
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch pets in search workflow: {e}")
            pets = []

    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]

    entity["results"] = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name", ""),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        }
        for p in pets
    ]

    return entity

@routes_bp.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    entity_data = {
        "type": data.type,
        "status": data.status or "available",
        "requested_at": datetime.utcnow().isoformat() + "Z",
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_search_request",
        entity_version=ENTITY_VERSION,
        entity=entity_data
    )

    return jsonify({"searchRequestId": entity_id})

@routes_bp.route("/favorites/add", methods=["POST"])
@validate_request(PetIdRequest)
async def favorites_add(data: PetIdRequest):
    user_id = "dummy_user"

    entity_data = {
        "user_id": user_id,
        "pet_id": data.petId,
        "action": "add",
        "requested_at": datetime.utcnow().isoformat() + "Z",
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="favorite_entity",
        entity_version=ENTITY_VERSION,
        entity=entity_data
    )

    return jsonify({"message": "Pet added to favorites", "favoriteCount": entity_data.get("favoriteCount", 0)})

@routes_bp.route("/favorites/remove", methods=["POST"])
@validate_request(PetIdRequest)
async def favorites_remove(data: PetIdRequest):
    user_id = "dummy_user"

    entity_data = {
        "user_id": user_id,
        "pet_id": data.petId,
        "action": "remove",
        "requested_at": datetime.utcnow().isoformat() + "Z",
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="favorite_entity",
        entity_version=ENTITY_VERSION,
        entity=entity_data
    )

    return jsonify({"message": "Pet removed from favorites", "favoriteCount": entity_data.get("favoriteCount", 0)})

@routes_bp.route("/favorites", methods=["GET"])
async def favorites_get():
    user_id = "dummy_user"
    favorite_entity_model = "favorite_record"

    try:
        favorites_list = await entity_service.search_items(
            token=cyoda_auth_service,
            entity_model=favorite_entity_model,
            entity_version=ENTITY_VERSION,
            filters={"user_id": user_id},
        )
    except Exception as e:
        logger.error(f"Failed to fetch favorites for user {user_id}: {e}")
        favorites_list = []

    pet_ids = {fav.get("pet_id") for fav in favorites_list if fav.get("pet_id")}

    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = []
        for pet_id in pet_ids:
            tasks.append(client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}"))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for resp in responses:
            if isinstance(resp, Exception):
                logger.warning(f"Error fetching pet in favorites_get: {resp}")
                continue
            if resp.status_code == 200:
                pets.append(resp.json())

    def pet_to_response_obj(pet: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "photoUrls": pet.get("photoUrls", []),
        }

    return jsonify({"favorites": [pet_to_response_obj(p) for p in pets]})

@routes_bp.route("/pet", methods=["POST"])
async def add_pet():
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Missing pet data"}), 400
    # Assume validation done elsewhere or here if needed

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="pet_entity",
        entity_version=ENTITY_VERSION,
        entity=data
    )
    return jsonify({"message": "Pet entity added", "entityId": entity_id})