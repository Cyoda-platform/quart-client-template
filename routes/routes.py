from dataclasses import dataclass
from typing import Optional, Literal
from quart import Blueprint, jsonify, request
from quart_schema import validate_request
import logging
from datetime import datetime
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

favorite_cats: set = set()

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

@dataclass
class CatsDataRequest:
    type: Literal["random", "breed"]
    breed_name: Optional[str] = None

@dataclass
class FavoriteCatRequest:
    cat_id: str

@routes_bp.route("/cats/data", methods=["POST"])
@validate_request(CatsDataRequest)
async def post_cats_data(data: CatsDataRequest):
    entity_data = data.__dict__
    entity_data["status"] = "processing"
    entity_data["created_at"] = datetime.utcnow().isoformat()
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cats",
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
        return jsonify({"entity_id": entity_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception("Failed to add cats entity")
        return jsonify({"error": "Failed to start cats data processing"}), 500

@routes_bp.route("/cats", methods=["GET"])
async def get_cats():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cats",
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"cats": [], "message": "No cat data available. Trigger POST /cats/data to fetch."}), 200

        completed_items = [item for item in items if item.get("status") == "completed"]
        if not completed_items:
            return jsonify({"cats": [], "message": "No completed cat data available yet."}), 200

        latest = max(completed_items, key=lambda e: e.get("created_at", ""))
        cats = latest.get("cats", [])
        return jsonify({"cats": cats}), 200

    except Exception as e:
        logger.exception("Error retrieving cats data")
        return jsonify({"cats": [], "message": "Error retrieving cats data."}), 500

@routes_bp.route("/cats/favorite", methods=["POST"])
@validate_request(FavoriteCatRequest)
async def post_favorite_cat(data: FavoriteCatRequest):
    cat_id = data.cat_id
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cats",
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"status": "failure", "message": "No cat data available to validate cat_id"}), 404

        completed_items = [item for item in items if item.get("status") == "completed"]
        if not completed_items:
            return jsonify({"status": "failure", "message": "No completed cat data available to validate cat_id"}), 404

        latest = max(completed_items, key=lambda e: e.get("created_at", ""))
        cats = latest.get("cats", [])
        if not any(cat["id"] == cat_id for cat in cats):
            return jsonify({"status": "failure", "message": "Invalid 'cat_id', not found in cached cats"}), 404

        favorite_cats.add(cat_id)
        return jsonify({"status": "success", "message": f"Cat {cat_id} added to favorites."}), 200

    except Exception as e:
        logger.exception("Error validating cat_id")
        return jsonify({"status": "failure", "message": "Error validating cat_id"}), 500