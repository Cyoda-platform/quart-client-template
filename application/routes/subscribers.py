"""
Subscriber Routes for the newsletter application.

Manages all Subscriber-related API endpoints including signup, list, and unsubscribe.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.subscriber import Subscriber
from services.services import get_entity_service


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
        201: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    },
)
async def create_subscriber(data: Subscriber) -> ResponseReturnValue:
    """Create a new subscriber (signup)"""
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
        logger.warning("Validation error creating Subscriber: %s", str(e))
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
        404: (Dict[str, Any], None),
        400: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
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

    except ValueError as e:
        logger.warning("Invalid entity ID %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INVALID_ID"}, 400
    except Exception as e:
        logger.exception("Error getting Subscriber %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscribers_bp.route("", methods=["GET"])
@tag(["subscribers"])
@operation_id("list_subscribers")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def list_subscribers() -> ResponseReturnValue:
    """List all subscribers"""
    try:
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)

        results = await service.find_all(
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
            limit=limit,
            offset=offset,
        )

        entities = [_to_entity_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200

    except Exception as e:
        logger.exception("Error listing Subscribers: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@subscribers_bp.route("/<entity_id>/unsubscribe", methods=["POST"])
@tag(["subscribers"])
@operation_id("unsubscribe")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, Any], None),
        500: (Dict[str, Any], None),
    }
)
async def unsubscribe(entity_id: str) -> ResponseReturnValue:
    """Unsubscribe a subscriber"""
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

        await service.transition(
            entity_id=entity_id,
            entity_class=Subscriber.ENTITY_NAME,
            entity_version=str(Subscriber.ENTITY_VERSION),
            transition_name="unsubscribe",
        )

        logger.info("Subscriber %s unsubscribed", entity_id)
        return {"message": "Unsubscribed successfully"}, 200

    except Exception as e:
        logger.exception("Error unsubscribing %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500
