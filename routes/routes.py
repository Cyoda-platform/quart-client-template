from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
from datetime import datetime

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

# Data classes for request validation

@dataclass
class FetchFilters:
    breed: Optional[str] = None
    age: Optional[str] = None
    location: Optional[str] = None

@dataclass
class CatsFetchRequest:
    source: str
    filters: Optional[Dict[str, Any]] = None  # Dynamic, no strict validation on filters content

@dataclass
class FavoriteRequest:
    user_id: str
    cat_id: str

# In-memory stores for favorites and cat cache
user_favorites = {}  # user_id -> set(cat_id)
cat_cache = {}       # cat_id -> cat info dict


async def process_cats_favorite(entity: dict):
    """
    Example workflow for favorite entity if needed.
    Here we just update timestamps or validate if needed.
    """
    entity['addedAt'] = datetime.utcnow().isoformat()
    return entity


@routes_bp.route("/cats/fetch", methods=["POST"])
@validate_request(CatsFetchRequest)
async def cats_fetch(data: CatsFetchRequest):
    """
    Endpoint now only adds entity with workflow function. All async processing moved to workflow.
    """
    entity_dict = data.__dict__

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="cats_fetch_request",
        entity_version=ENTITY_VERSION,
        entity=entity_dict,
    )

    return jsonify({
        "entity_id": entity_id,
        "message": "Cats fetch request accepted and processing started.",
    }), 202


@routes_bp.route("/cats/results/<entity_id>", methods=["GET"])
async def cats_results(entity_id):
    """
    Retrieve results by entity_id.
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="cats_fetch_request",
            entity_version=ENTITY_VERSION,
            entity_id=entity_id,
        )
    except Exception as e:
        logger.warning(f"Entity {entity_id} not found: {e}")
        return jsonify({"error": "Entity not found"}), 404

    return jsonify({
        "entity_id": entity_id,
        "status": entity.get("status", "processing"),
        "requestedAt": entity.get("requestedAt"),
        "completedAt": entity.get("completedAt"),
        "data": entity.get("data", []),
        "error": entity.get("error"),
    }), 200


@routes_bp.route("/cats/favorites", methods=["POST"])
@validate_request(FavoriteRequest)
async def add_favorite(data: FavoriteRequest):
    user_id = data.user_id
    cat_id = data.cat_id
    if not user_id or not cat_id:
        return jsonify({"success": False, "message": "user_id and cat_id are required"}), 400

    if user_id not in user_favorites:
        user_favorites[user_id] = set()
    user_favorites[user_id].add(cat_id)

    if cat_id not in cat_cache:
        cat_cache[cat_id] = {
            "id": cat_id,
            "breed": "Unknown",
            "image_url": None,
        }

    return jsonify({"success": True, "message": "Cat added to favorites"}), 200


@routes_bp.route("/cats/favorites/<user_id>", methods=["GET"])
async def get_favorites(user_id):
    favs = user_favorites.get(user_id, set())
    favorites_list = []
    for cat_id in favs:
        cat = cat_cache.get(cat_id)
        if cat:
            favorites_list.append(
                {
                    "cat_id": cat_id,
                    "breed": cat.get("breed", "Unknown"),
                    "image_url": cat.get("image_url"),
                }
            )
        else:
            favorites_list.append({"cat_id": cat_id, "breed": "Unknown", "image_url": None})

    return jsonify({"user_id": user_id, "favorites": favorites_list}), 200