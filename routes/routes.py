from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify
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
    status: Optional[str] = None

@dataclass
class PetDetailsRequest:
    petId: str  # petId is string

@dataclass
class PetFavoriteRequest:
    petId: str  # petId is string

PET_ENTITY_NAME = "pet"
PET_FETCH_ENTITY_NAME = "pet_fetch"
PET_DETAIL_ENTITY_NAME = "pet_detail"
FAVORITE_PET_ENTITY_NAME = "favorite_pet"

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Workflow function for pet entity enrichment
async def process_pet(entity: dict) -> dict:
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'
    return entity

# Workflow function to fetch pets and add pet entities
async def process_pet_fetch(entity: dict) -> dict:
    status = entity.get('status')
    url = f"https://petstore.swagger.io/v2/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
            for pet in pets:
                pet_entity = {
                    "id": str(pet.get("id")),
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name") if pet.get("category") else None,
                    "status": pet.get("status"),
                }
                # Add pet entity with its own workflow
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=PET_ENTITY_NAME,
                    entity_version=ENTITY_VERSION,
                    entity=pet_entity
                )
        except Exception:
            logger.exception("Failed to fetch pets from petstore in process_pet_fetch")

    entity['fetched_at'] = datetime.utcnow().isoformat() + 'Z'
    return entity

# Workflow function to fetch pet detail and update pet entity
async def process_pet_detail(entity: dict) -> dict:
    pet_id = entity.get("id") or entity.get("petId")
    if not pet_id:
        logger.warning("No petId provided to process_pet_detail")
        return entity

    url = f"https://petstore.swagger.io/v2/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            pet_detail = r.json()
            pet_entity = {
                "id": str(pet_detail.get("id")),
                "name": pet_detail.get("name"),
                "category": pet_detail.get("category", {}).get("name") if pet_detail.get("category") else None,
                "status": pet_detail.get("status"),
                "photoUrls": pet_detail.get("photoUrls"),
                "tags": pet_detail.get("tags"),
                "processed_at": datetime.utcnow().isoformat() + 'Z',
            }
            # Add or update pet entity (add_item acts as upsert)
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=pet_entity
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Pet with id {pet_id} not found in petstore")
            else:
                logger.exception(f"HTTP error fetching pet detail for id={pet_id}")
        except Exception:
            logger.exception(f"Failed to fetch pet detail for id={pet_id}")

    entity['detail_fetched_at'] = datetime.utcnow().isoformat() + 'Z'
    return entity

# Workflow function for validating and enriching favorite_pet entity
async def process_favorite_pet(entity: dict) -> dict:
    pet_id = entity.get("petId")
    if not pet_id:
        logger.warning("favorite_pet entity missing petId")
        entity['valid'] = False
        return entity

    pet = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model=PET_ENTITY_NAME,
        entity_version=ENTITY_VERSION,
        technical_id=pet_id
    )
    if not pet:
        logger.warning(f"Trying to favorite pet that does not exist: {pet_id}")
        entity['valid'] = False
    else:
        entity['valid'] = True
        entity['favorited_at'] = datetime.utcnow().isoformat() + 'Z'
    return entity

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)
async def post_pets_fetch(data: PetFetchRequest):
    fetch_entity = {
        "status": data.status
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_FETCH_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=fetch_entity
        )
        return jsonify({"message": "Pet fetch triggered"})
    except Exception:
        logger.exception("Failed to trigger pet fetch")
        return jsonify({"error": "Failed to trigger pet fetch"}), 500

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify(items)
    except Exception:
        logger.exception("Failed to get pets")
        return jsonify({"error": "Failed to get pets"}), 500

@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def post_pet_details(data: PetDetailsRequest):
    detail_entity = {"id": data.petId}
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_DETAIL_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=detail_entity
        )
        return jsonify({"message": "Pet detail fetch triggered", "petId": data.petId})
    except Exception:
        logger.exception("Failed to trigger pet detail fetch")
        return jsonify({"error": "Failed to trigger pet detail fetch"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet_detail(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": "Pet details not found"}), 404
        return jsonify(pet)
    except Exception:
        logger.exception(f"Failed to get pet detail for id={pet_id}")
        return jsonify({"error": "Failed to get pet details"}), 500

@app.route("/pets/favorite", methods=["POST"])
@validate_request(PetFavoriteRequest)
async def post_pet_favorite(data: PetFavoriteRequest):
    favorite_entity = {
        "petId": data.petId
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=FAVORITE_PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=favorite_entity
        )
        return jsonify({"message": "Pet marked as favorite", "petId": data.petId})
    except Exception:
        logger.exception("Failed to mark pet as favorite")
        return jsonify({"error": "Failed to mark pet as favorite"}), 500

@app.route("/pets/favorites", methods=["GET"])
async def get_pets_favorites():
    try:
        favorite_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=FAVORITE_PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        favorite_pets = []
        for fav in favorite_entities:
            if not fav.get("valid", True):
                continue  # skip invalid favorites
            pet_id = fav.get("petId")
            if not pet_id:
                continue
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
            )
            if pet:
                favorite_pets.append(pet)
        return jsonify(favorite_pets)
    except Exception:
        logger.exception("Failed to get favorite pets")
        return jsonify({"error": "Failed to get favorite pets"}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
