from dataclasses import dataclass
import logging
import uuid
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

@dataclass
class CatFetchRequest:
    type: str  # "image" or "fact"


@routes_bp.route("/cats/fetch", methods=["POST"])
@validate_request(CatFetchRequest)
async def cats_fetch(data: CatFetchRequest):
    """
    POST /cats/fetch
    Request JSON: { "type": "image" | "fact" }
    Response JSON: { "requestId": "string" }
    """
    try:
        # Validate input explicitly even if dataclass is used
        if data.type not in ("image", "fact"):
            return jsonify({"error": "Invalid type. Must be 'image' or 'fact'."}), 400

        # Prepare a minimal entity dict for persistence
        entity_dict = {
            "type": data.type,
        }

        # Add item with workflow function - processing happens inside workflow
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="CatFetchRequest",
            entity_version=ENTITY_VERSION,
            entity=entity_dict,
        )

        return jsonify({"requestId": entity_id})

    except Exception as e:
        logger.exception(f"Error in /cats/fetch endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


@routes_bp.route("/cats/result/<string:request_id>", methods=["GET"])
async def cats_result(request_id: str):
    """
    GET /cats/result/{requestId}
    Response JSON:
    {
      "requestId": "string",
      "type": "image" | "fact",
      "data": "string",
      "status": "processing" | "completed" | "failed",
      "requestedAt": "ISO8601 string"
    }
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="CatFetchRequest",
            entity_version=ENTITY_VERSION,
            entity_id=request_id,
        )
        if entity is None:
            return jsonify({"error": "requestId not found"}), 404

        # Defensive defaults
        response = {
            "requestId": request_id,
            "type": entity.get("type", "unknown"),
            "data": entity.get("data"),
            "status": entity.get("status", "processing"),
            "requestedAt": entity.get("requestedAt"),
        }
        return jsonify(response)

    except Exception as e:
        logger.exception(f"Error in /cats/result/{request_id} endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500