from dataclasses import dataclass
from typing import List, Optional, Dict, Any
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

CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

@dataclass
class FetchDataRequest:
    types: List[str]
    filters: Optional[Dict[str, Any]] = None

@dataclass
class FavoriteRequest:
    type: str
    content: str

@routes_bp.route("/cats/fetch-data", methods=["POST"])
@validate_request(FetchDataRequest)
async def cats_fetch_data(data: FetchDataRequest):
    """
    Endpoint calls entity_service.add_item with workflow.
    The workflow fetches and enriches data.
    """
    entity = data.__dict__
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="fetch_data",
            entity_version=ENTITY_VERSION,
            entity=entity,
            )
        # Return enriched entity immediately after processing (before persistence completes might be possible)
        return jsonify(entity)
    except Exception:
        logger.exception("Error in /cats/fetch-data")
        return jsonify({"error": "Failed to fetch cat data"}), 500

@routes_bp.route("/cats/favorite", methods=["POST"])
@validate_request(FavoriteRequest)
async def cats_favorite(data: FavoriteRequest):
    """
    Endpoint validates input then persists favorite entity with workflow.
    """
    fav_type = data.type
    content = data.content

    if fav_type not in ("image", "fact") or not content:
        return jsonify({"error": "Invalid favorite submission"}), 400

    fav_record = {
        "type": fav_type,
        "content": content,
        "submittedAt": datetime.utcnow().isoformat()
    }

    try:
        fav_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            entity=fav_record,
            )
        return jsonify({"status": "success", "message": "Favorite saved.", "id": fav_id})
    except Exception:
        logger.exception("Failed to save favorite")
        return jsonify({"error": "Failed to save favorite"}), 500

@routes_bp.route("/cats/results", methods=["GET"])
async def cats_results():
    """
    Returns latest cached cat data from entity_service.
    Queries latest fetch_data entity and returns requested data type.
    """
    try:
        data_type = request.args.get("type")
        valid_types = {"facts", "images", "breeds"}
        if data_type not in valid_types:
            return jsonify({"error": f"Invalid type '{data_type}'. Must be one of {valid_types}."}), 400

        latest_entity = await entity_service.get_latest_entity_by_model(
            token=cyoda_auth_service,
            entity_model="fetch_data",
            entity_version=ENTITY_VERSION
        )

        if not latest_entity:
            return jsonify({"type": data_type, "data": []})

        data = latest_entity.get(data_type, [])
        if data is None:
            data = []

        return jsonify({"type": data_type, "data": data})
    except Exception:
        logger.exception("Error in /cats/results")
        return jsonify({"error": "Failed to retrieve cat data"}), 500