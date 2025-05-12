from dataclasses import dataclass
from typing import List, Optional

import logging
from datetime import datetime

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

# Data classes for validation


@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None


@dataclass
class FavoritePet:
    petId: int


@dataclass
class AdoptionStatusRequest:
    petIds: List[int]


# Local cache for adoption status - no replacement possible
adoption_status_cache: dict[int, dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


# Helpers


def _filter_key(data: dict) -> str:
    return str(sorted(data.items()))


async def fetch_pets_from_petstore(filters: dict) -> List[dict]:
    status = filters.get("status", "available")
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []

    filtered = []
    pet_type = filters.get("type")
    name_filter = filters.get("name", "").lower()

    for pet in pets:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            continue
        if name_filter and name_filter not in pet.get("name", "").lower():
            continue
        filtered.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", ""),
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", []) if tag.get("name")] if pet.get("tags") else [],
                "photoUrls": pet.get("photoUrls", []),
            }
        )
    return filtered


async def calculate_adoption_status(pet_ids: List[int]) -> List[dict]:
    statuses = []
    for pid in pet_ids:
        ready = (pid % 2 == 0)
        statuses.append(
            {
                "petId": pid,
                "readyForAdoption": ready,
                "notes": "Ready for adoption" if ready else "Needs more care",
            }
        )
    return statuses


# Workflow functions


async def process_favorite_pet(entity: dict):
    # Add ISO8601 UTC timestamp
    entity["addedAt"] = datetime.utcnow().isoformat() + "Z"


async def process_pet_search(entity: dict):
    filters = {
        "type": entity.get("type"),
        "status": entity.get("status"),
        "name": entity.get("name"),
    }
    pets = await fetch_pets_from_petstore(filters)

    # entity might not have 'id' yet, generate unique id for cache entity
    # Use current timestamp + filters hash as fallback cache key
    cache_key = entity.get("id")
    if not cache_key:
        import hashlib
        import time

        key_str = f"{datetime.utcnow().isoformat()}_{str(sorted(filters.items()))}"
        cache_key = hashlib.sha256(key_str.encode()).hexdigest()

    cache_entity = {
        "searchId": cache_key,
        "filters": filters,
        "pets": pets,
        "cachedAt": datetime.utcnow().isoformat() + "Z",
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_result",
            entity_version=ENTITY_VERSION,
            entity=cache_entity,
        )
    except Exception as e:
        logger.error(f"Failed to save pet_search_result entity: {e}")


async def process_pet_adoption_status_request(entity: dict):
    pet_ids = entity.get("petIds", [])
    statuses = await calculate_adoption_status(pet_ids)

    for s in statuses:
        adoption_status_cache[s["petId"]] = s

    request_id = entity.get("id")
    # If no id yet, generate fallback id to avoid entity_service errors
    if not request_id:
        import hashlib
        import time

        key_str = f"{datetime.utcnow().isoformat()}_{str(sorted(pet_ids))}"
        request_id = hashlib.sha256(key_str.encode()).hexdigest()

    for status in statuses:
        status_entity = {
            "requestId": request_id,
            "petId": status["petId"],
            "readyForAdoption": status["readyForAdoption"],
            "notes": status["notes"],
            "calculatedAt": datetime.utcnow().isoformat() + "Z",
        }
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet_adoption_status",
                entity_version=ENTITY_VERSION,
                entity=status_entity,
            )
        except Exception as e:
            logger.error(f"Failed to save pet_adoption_status entity for petId {status['petId']}: {e}")


# Routes


@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    search_data = data.__dict__.copy()
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search",
            entity_version=ENTITY_VERSION,
            entity=search_data,
            workflow=process_pet_search,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process pet search"}), 500

    return jsonify({"searchId": id})


@app.route("/pets/favorite", methods=["POST"])
@validate_request(FavoritePet)
async def pets_favorite(data: FavoritePet):
    pet_id = data.petId
    favorite_pet_data = {"petId": pet_id}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite_pet",
            entity_version=ENTITY_VERSION,
            entity=favorite_pet_data,
            workflow=process_favorite_pet,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add favorite pet"}), 500

    return jsonify({"id": id})


@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    try:
        favorites = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="favorite_pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch favorite pets"}), 500

    if not favorites:
        return jsonify({"pets": []})

    pet_ids = [fav.get("petId") for fav in favorites if fav.get("petId") is not None]

    pets = []

    async with httpx.AsyncClient() as client:
        for pid in pet_ids:
            try:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pid}", timeout=10)
                resp.raise_for_status()
                pet = resp.json()
                pets.append(
                    {
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name", ""),
                        "status": pet.get("status"),
                        "tags": [tag.get("name") for tag in pet.get("tags", []) if tag.get("name")] if pet.get("tags") else [],
                        "photoUrls": pet.get("photoUrls", []),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to fetch pet details for petId {pid}: {e}")

    return jsonify({"pets": pets})


@app.route("/pets/adoption-status", methods=["POST"])
@validate_request(AdoptionStatusRequest)
async def pets_adoption_status(data: AdoptionStatusRequest):
    request_data = {"petIds": data.petIds}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_adoption_status_request",
            entity_version=ENTITY_VERSION,
            entity=request_data,
            workflow=process_pet_adoption_status_request,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process adoption status request"}), 500

    return jsonify({"requestId": id})


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)