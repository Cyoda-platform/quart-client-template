"""
Subscriber Routes for Weekly Cat Fact Subscription Application

Manages all Subscriber-related API endpoints including CRUD operations,
subscription management, and unsubscribe functionality.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.subscriber.version_1.subscriber import Subscriber


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


subscribers_bp = Blueprint("subscribers", __name__, url_prefix="/api/subscribers")


@subscribers_bp.route("", methods=["POST"])
@tag(["subscribers"])
@operation_id("create_subscriber")
@validate(
    request=Subscriber,
    responses={
        201: (dict, None),
        400: (dict, None),
        500: (dict, None),
    },
)
async def create_subscriber(data: Subscriber) -> ResponseReturnValue:
    """Create a new Subscriber (signup)"""
    try:
        entity_data = data.model_dump(by_alias=True)
        # Generate unsubscribe token if not provided
        if not entity_data.get("unsubscribeToken"):
            entity_data["unsubscribeToken"] = str(uuid.uuid4())

        response = await service.save(
            entity=entity_data,
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
        )
        logger.info("Created Subscriber with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Subscriber: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscribers_bp.route("/<entity_id>", methods=["GET"])
@tag(["subscribers"])
@operation_id("get_subscriber")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def get_subscriber(entity_id: str) -> ResponseReturnValue:
    """Get Subscriber by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Subscriber not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting Subscriber: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscribers_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["subscribers"])
@operation_id("delete_subscriber")
@validate(
    responses={
        200: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def delete_subscriber(entity_id: str) -> ResponseReturnValue:
    """Delete Subscriber by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete(
            entity_id=entity_id,
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
        )

        return {"message": "Subscriber deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting Subscriber: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

