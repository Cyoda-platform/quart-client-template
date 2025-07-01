from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

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
class QueryPetsRequest:
    category: Optional[str]
    status: Optional[str]
    sort_by: Optional[str]
    sort_order: Optional[str]
    limit: int
    offset: int

@dataclass
class PetIdRequest:
    pet_id: str  # id is now string per requirements

PET_ENTITY_NAME = "pet"

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(
    filters: dict, sort_by: Optional[str], sort_order: Optional[str], limit: int, offset: int
) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            status = filters.get("status")
            if status:
                url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                params = {"status": status}
                response = await client.get(url, params=params)
            else:
                pets = []
                for s in ["available", "pending", "sold"]:
                    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                    r = await client.get(url, params={"status": s})
                    if r.status_code == 200:
                        pets.extend(r.json())
                response = None
            if response and response.status_code == 200:
                pets = response.json()
            elif response:
                logger.error(f"Petstore API error: {response.status_code} {response.text}")
                pets = []
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            pets = []

    category_filter = filters.get("category")
    if category_filter:
        pets = [
            pet
            for pet in pets
            if pet.get("category") and pet["category"].get("name", "").lower() == category_filter.lower()
        ]

    if sort_by:
        reverse = sort_order == "desc"
        def sort_key(p):
            if sort_by == "category":
                return p.get("category", {}).get("name", "").lower()
            return p.get(sort_by, "")
        pets.sort(key=sort_key, reverse=reverse)

    total_count = len(pets)
    pets = pets[offset : offset + limit]

    result_pets = []
    for p in pets:
        result_pets.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "category": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "photoUrls": p.get("photoUrls", []),
                "tags": [t["name"] for t in p.get("tags", []) if "name" in t],
            }
        )

    return {"pets": result_pets, "total_count": total_count}

@app.route("/pets/query", methods=["POST"])
@validate_request(QueryPetsRequest)
async def pets_query(data: QueryPetsRequest):
    filters = {}
    if data.category:
        filters["category"] = data.category
    if data.status:
        filters["status"] = data.status
    pets_data = await fetch_pets_from_petstore(
        filters, data.sort_by, data.sort_order, data.limit, data.offset
    )
    return jsonify(pets_data)

def get_user_id() -> str:
    # Placeholder for actual auth logic
    return "default_user"

# Workflow function for "favorite" entity
async def process_favorite(entity_data: dict):
    """
    Workflow function applied to the 'favorite' entity before persistence.
    Adds timestamp and enriches entity with pet name & category from Petstore API.
    """
    # Add timestamp if not present
    if "added_at" not in entity_data:
        entity_data["added_at"] = datetime.utcnow().isoformat()

    pet_id = entity_data.get("pet_id")
    if not pet_id:
        logger.warning("Favorite entity missing pet_id, skipping enrichment")
        return entity_data

    # Fetch pet info from Petstore API asynchronously
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
            resp = await client.get(url)
            if resp.status_code == 200:
                pet = resp.json()
                entity_data["pet_name"] = pet.get("name")
                entity_data["pet_category"] = pet.get("category", {}).get("name")
            else:
                logger.warning(f"Failed to fetch pet info for pet_id {pet_id}, status: {resp.status_code}")
        except Exception as e:
            logger.exception(f"Exception during fetching pet info for pet_id {pet_id}: {e}")

    return entity_data

@app.route("/favorites/add", methods=["POST"])
@validate_request(PetIdRequest)
async def favorites_add(data: PetIdRequest):
    pet_id = str(data.pet_id)
    user_id = get_user_id()
    favorite_data = {
        "user_id": user_id,
        "pet_id": pet_id,
    }
    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            entity=favorite_data
        )
        logger.info(f"User {user_id} added pet {pet_id} to favorites with id {new_id}")
        return jsonify({"success": True, "message": "Pet added to favorites.", "id": new_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Failed to add favorite."}), 500

@app.route("/favorites/remove", methods=["POST"])
@validate_request(PetIdRequest)
async def favorites_remove(data: PetIdRequest):
    pet_id = str(data.pet_id)
    user_id = get_user_id()
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.user_id",
                    "operatorType": "EQUALS",
                    "value": user_id,
                    "type": "simple",
                },
                {
                    "jsonPath": "$.pet_id",
                    "operatorType": "EQUALS",
                    "value": pet_id,
                    "type": "simple",
                },
            ],
        }
    }
    try:
        favorites = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
        if not favorites:
            return jsonify({"success": False, "message": "Pet not in favorites"}), 400
        for fav in favorites:
            fav_id = str(fav.get("id"))
            await entity_service.delete_item(
                token=cyoda_auth_service,
                entity_model="favorite",
                entity_version=ENTITY_VERSION,
                technical_id=fav_id,
                meta={},
            )
        logger.info(f"User {user_id} removed pet {pet_id} from favorites")
        return jsonify({"success": True, "message": "Pet removed from favorites."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Failed to remove favorite."}), 500

@app.route("/favorites", methods=["GET"])
async def favorites_list():
    user_id = get_user_id()
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.user_id",
                    "operatorType": "EQUALS",
                    "value": user_id,
                    "type": "simple",
                }
            ],
        }
    }
    try:
        favorites = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"favorites": []})

    pet_ids = [str(fav.get("pet_id")) for fav in favorites if fav.get("pet_id")]

    async with httpx.AsyncClient(timeout=10.0) as client:
        async def fetch_pet(pet_id: str):
            try:
                url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
                r = await client.get(url)
                if r.status_code == 200:
                    p = r.json()
                    return {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "category": p.get("category", {}).get("name"),
                        "status": p.get("status"),
                        "photoUrls": p.get("photoUrls", []),
                    }
                else:
                    logger.warning(f"Petstore API returned {r.status_code} for pet {pet_id}")
                    return None
            except Exception as e:
                logger.exception(f"Error fetching pet {pet_id} details: {e}")
                return None

        pet_details_results = await asyncio.gather(*[fetch_pet(pid) for pid in pet_ids])
        favorites_pets = [pet for pet in pet_details_results if pet is not None]

    return jsonify({"favorites": favorites_pets})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
