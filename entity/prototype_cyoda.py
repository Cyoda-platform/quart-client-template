from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

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

# Data models for validation
@dataclass
class SearchCriteria:
    status: str
    type: str

@dataclass
class FavoriteData:
    userId: str
    petId: int

@dataclass
class ReviewData:
    userId: str
    petId: int
    rating: int
    comment: str

# External Petstore API base URL (Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(criteria: dict) -> List[dict]:
    """Query the external Petstore API /pet/findByStatus endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            status = criteria.get("status", "")
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            response = await client.get(url, params={"status": status})
            response.raise_for_status()
            pets = response.json()
            pet_type = criteria.get("type")
            if pet_type:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
    except Exception as e:
        logger.exception(f"Failed fetching pets from Petstore: {e}")
        return []


@app.route("/pets/search", methods=["POST"])
# Issue workaround: validate_request must come after route decorator for POST due to quart-schema defect
@validate_request(SearchCriteria)
async def search_pets(data: SearchCriteria):
    try:
        criteria = {"status": data.status, "type": data.type}
        pets = await fetch_pets_from_petstore(criteria)
        result = []
        for pet in pets:
            result.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", []),
            })
        return jsonify({"pets": result})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/favorite", methods=["POST"])
# Issue workaround: validate_request must come after route decorator for POST due to quart-schema defect
@validate_request(FavoriteData)
async def add_favorite_pet(data: FavoriteData):
    try:
        # refactor to use entity_service to add favorite
        entity_name = "favorite_pet"
        # convert petId to string for technical id
        data_dict = {
            "userId": data.userId,
            "petId": data.petId
        }
        # add_item returns id only
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        return jsonify({"id": new_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/favorites/<string:user_id>", methods=["GET"])
async def get_favorite_pets(user_id):
    try:
        entity_name = "favorite_pet"
        # retrieve all favorite_pet items and filter by userId = user_id
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.userId",
                        "operatorType": "EQUALS",
                        "value": user_id,
                        "type": "simple"
                    }
                ]
            }
        }
        favorites = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        pet_ids = [fav.get("petId") for fav in favorites if fav.get("petId") is not None]

        pets = []
        async with httpx.AsyncClient(timeout=10) as client:
            for pet_id in pet_ids:
                try:
                    res = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                    if res.status_code == 200:
                        pet = res.json()
                        pets.append({
                            "id": pet.get("id"),
                            "name": pet.get("name"),
                            "type": pet.get("category", {}).get("name"),
                            "status": pet.get("status"),
                        })
                    else:
                        logger.warning(f"Pet id={pet_id} not found in Petstore")
                except Exception as e:
                    logger.exception(f"Error fetching pet id={pet_id}: {e}")
        return jsonify({"favorites": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/review", methods=["POST"])
# Issue workaround: validate_request must come after route decorator for POST due to quart-schema defect
@validate_request(ReviewData)
async def submit_pet_review(data: ReviewData):
    try:
        if not (1 <= data.rating <= 5):
            return jsonify({"error": "rating must be between 1 and 5"}), 400
        entity_name = "pet_review"
        review_data = {
            "userId": data.userId,
            "petId": data.petId,
            "rating": data.rating,
            "comment": data.comment,
            "submittedAt": datetime.utcnow().isoformat() + "Z",
        }
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=review_data
        )
        return jsonify({"id": new_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/pets/reviews/<string:pet_id>", methods=["GET"])
async def get_pet_reviews(pet_id):
    try:
        entity_name = "pet_review"
        # pet_id string, filter by petId
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.petId",
                        "operatorType": "EQUALS",
                        "value": int(pet_id),  # petId is numeric in reviews, convert back here to int for condition
                        "type": "simple"
                    }
                ]
            }
        }
        pet_reviews = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify({"reviews": pet_reviews})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)