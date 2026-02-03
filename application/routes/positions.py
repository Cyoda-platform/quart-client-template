"""
Position Routes for Institutional Trading Platform

Manages all Position-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.exception import is_not_found
from services.services import get_entity_service

from application.entity.position.version_1.position import Position


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()
logger = logging.getLogger(__name__)


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


@positions_bp.route("", methods=["POST"])
@tag(["positions"])
@operation_id("create_position")
@validate(request=Position, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)})
async def create_position(data: Position) -> ResponseReturnValue:
    """Create a new position"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating position: {str(e)}")
        return {"error": str(e)}, 500


@positions_bp.route("/<entity_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_position")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_position(entity_id: str) -> ResponseReturnValue:
    """Get a position by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        if is_not_found(response):
            return {"error": "Position not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting position: {str(e)}")
        return {"error": str(e)}, 500


@positions_bp.route("", methods=["GET"])
@tag(["positions"])
@operation_id("list_positions")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_positions() -> ResponseReturnValue:
    """List all positions"""
    try:
        response = await service.list(
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
            limit=100,
            offset=0,
        )
        return {"positions": [_to_entity_dict(item) for item in response.data]}, 200
    except Exception as e:
        logger.error(f"Error listing positions: {str(e)}")
        return {"error": str(e)}, 500


@positions_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["positions"])
@operation_id("transition_position")
@validate(request=dict, responses={200: (dict, None), 400: (dict, None), 500: (dict, None)})
async def transition_position(entity_id: str, data: dict) -> ResponseReturnValue:
    """Trigger a workflow transition on a position"""
    try:
        transition_name = data.get("transitionName")
        if not transition_name:
            return {"error": "transitionName is required"}, 400

        response = await service.transition(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
            transition_name=transition_name,
        )
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error transitioning position: {str(e)}")
        return {"error": str(e)}, 500

