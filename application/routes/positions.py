"""
Position routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.position import Position
from common.exception import is_not_found
from services.services import get_entity_service

logger = logging.getLogger(__name__)

positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@positions_bp.route("", methods=["POST"])
@tag(["positions"])
@operation_id("create_position")
@validate(request=Position, responses={201: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def create_position(data: Position) -> ResponseReturnValue:
    """Create a new Position"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        logger.info("Created Position with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error("Error creating position: %s", str(e))
        return {"error": str(e)}, 500


@positions_bp.route("/<entity_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_position")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def get_position(entity_id: str) -> ResponseReturnValue:
    """Get a Position by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting position: %s", str(e))
        return {"error": str(e)}, 500


@positions_bp.route("", methods=["GET"])
@tag(["positions"])
@operation_id("list_positions")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def list_positions() -> ResponseReturnValue:
    """List all Positions"""
    try:
        response = await service.list(
            entity_class=Position.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing positions: %s", str(e))
        return {"error": str(e)}, 500
