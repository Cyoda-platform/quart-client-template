from dataclasses import dataclass
from typing import Optional

import logging
from quart import Blueprint, jsonify
from quart_schema import validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]


@dataclass
class BreedFilter:
    origin: Optional[str] = None
    temperament: Optional[str] = None


@dataclass
class FactsRequest:
    count: int


@dataclass
class ImagesRequest:
    breed_id: Optional[str] = None
    limit: int = 5


@dataclass
class FavoriteRequest:
    user_id: str
    item_type: str  # "breed" | "fact" | "image"
    item_id: str


@routes_bp.route("/cats/breeds", methods=["POST"])
@validate_request(BreedFilter)
async def post_cats_breeds(data: BreedFilter):
    entity = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="breeds_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
        )
        return jsonify({"message": "Breeds request accepted"}), 202
    except Exception as e:
        logger.exception("Failed to submit breeds request: %s", e)
        return jsonify({"message": "Failed to submit breeds request"}), 500


@routes_bp.route("/cats/breeds", methods=["GET"])
@validate_querystring(BreedFilter)
async def get_cats_breeds():
    try:
        breeds = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="breeds",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get breeds: %s", e)
        breeds = []
    return jsonify({"breeds": breeds or []})


@routes_bp.route("/cats/facts", methods=["POST"])
@validate_request(FactsRequest)
async def post_cats_facts(data: FactsRequest):
    entity = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="facts_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
        )
        return jsonify({"message": "Facts request accepted"}), 202
    except Exception as e:
        logger.exception("Failed to submit facts request: %s", e)
        return jsonify({"message": "Failed to submit facts request"}), 500


@routes_bp.route("/cats/facts", methods=["GET"])
async def get_cats_facts():
    try:
        facts = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="facts",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get facts: %s", e)
        facts = []
    return jsonify({"facts": facts or []})


@routes_bp.route("/cats/images", methods=["POST"])
@validate_request(ImagesRequest)
async def post_cats_images(data: ImagesRequest):
    entity = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="images_request",
            entity_version=ENTITY_VERSION,
            entity=entity,
        )
        return jsonify({"message": "Images request accepted"}), 202
    except Exception as e:
        logger.exception("Failed to submit images request: %s", e)
        return jsonify({"message": "Failed to submit images request"}), 500


@routes_bp.route("/cats/images", methods=["GET"])
async def get_cats_images():
    try:
        images = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="images",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get images: %s", e)
        images = []
    return jsonify({"images": images or []})


@routes_bp.route("/favorites", methods=["POST"])
@validate_request(FavoriteRequest)
async def post_favorites(data: FavoriteRequest):
    try:
        fav_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorites",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
        )
        return jsonify({"success": True, "id": fav_id, "message": "Added to favorites"})
    except Exception as e:
        logger.exception("Failed to add to favorites: %s", e)
        return jsonify({"success": False, "message": "Failed to add to favorites"}), 500


@routes_bp.route("/favorites/<string:user_id>", methods=["GET"])
async def get_favorites(user_id):
    try:
        condition = {"user_id": user_id}
        favs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="favorites",
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
    except Exception as e:
        logger.exception("Failed to get favorites: %s", e)
        favs = []
    return jsonify({"favorites": favs or []})