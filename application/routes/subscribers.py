"""
Subscriber Routes for email subscription management.

Manages all Subscriber-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.subscriber import Subscriber
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


subscribers_bp = Blueprint("subscribers", __name__, url_prefix="/api/subscribers")


@subscribers_bp.route("", methods=["POST"])
@tag(["subscribers"])
@operation_id("create_subscriber")
@validate(
    request=Subscriber,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_subscriber(data: Subscriber) -> ResponseReturnValue:
    """Create a new Subscriber"""
    try:
        entity_data = data.model_dump(by_alias=True)
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
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_subscriber(entity_id: str) -> ResponseReturnValue:
    """Get Subscriber by ID"""
    try:
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


@subscribers_bp.route("", methods=["GET"])
@tag(["subscribers"])
@operation_id("list_subscribers")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_subscribers() -> ResponseReturnValue:
    """List all Subscribers"""
    try:
        entities = await service.find_all(
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200

    except Exception as e:
        logger.exception("Error listing Subscribers: %s", str(e))
        return jsonify({"error": str(e)}), 500


@subscribers_bp.route("/<entity_id>", methods=["PUT"])
@tag(["subscribers"])
@operation_id("update_subscriber")
@validate(
    request=Subscriber,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def update_subscriber(entity_id: str, data: Subscriber) -> ResponseReturnValue:
    """Update Subscriber"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
        )
        logger.info("Updated Subscriber %s", entity_id)
        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error updating Subscriber: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscribers_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["subscribers"])
@operation_id("delete_subscriber")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def delete_subscriber(entity_id: str) -> ResponseReturnValue:
    """Delete Subscriber by ID"""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
        )
        logger.info("Deleted Subscriber %s", entity_id)
        return {"success": True, "message": "Subscriber deleted"}, 200

    except Exception as e:
        logger.exception("Error deleting Subscriber: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

