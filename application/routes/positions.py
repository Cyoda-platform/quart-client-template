"""
Position management API routes for the trading platform.

Provides REST endpoints for Position CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.position.version_1.position import Position
from services.services import get_entity_service

logger = logging.getLogger(__name__)

positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


@positions_bp.route("", methods=["POST"])
@validate_request(Position)
@validate_response(Position, status_code=201)
async def create_position(data: Position) -> tuple[Dict[str, Any], int]:
    """Create a new Position."""
    try:
        entity_service = get_entity_service()
        position_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=position_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        position_data["id"] = response.metadata.id
        position_data["state"] = response.metadata.state
        logger.info(f"Position created: {response.metadata.id}")
        return position_data, 201
    except Exception as e:
        logger.error(f"Failed to create Position: {str(e)}")
        return {"error": str(e)}, 400


@positions_bp.route("/<position_id>", methods=["GET"])
async def get_position(position_id: str) -> tuple[Dict[str, Any], int]:
    """Get Position by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=position_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "Position not found"}, 404
        position_data = response.data.model_dump(by_alias=True)
        position_data["id"] = response.metadata.id
        position_data["state"] = response.metadata.state
        return position_data, 200
    except Exception as e:
        logger.error(f"Failed to get Position: {str(e)}")
        return {"error": str(e)}, 404


@positions_bp.route("/<position_id>", methods=["PUT"])
@validate_request(Position)
async def update_position(
    position_id: str, data: Position
) -> tuple[Dict[str, Any], int]:
    """Update a Position."""
    try:
        entity_service = get_entity_service()
        position_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity_id=position_id,
            entity=position_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        position_data["id"] = response.metadata.id
        position_data["state"] = response.metadata.state
        logger.info(f"Position updated: {position_id}")
        return position_data, 200
    except Exception as e:
        logger.error(f"Failed to update Position: {str(e)}")
        return {"error": str(e)}, 400


@positions_bp.route("/<position_id>", methods=["DELETE"])
async def delete_position(position_id: str) -> tuple[Dict[str, str], int]:
    """Delete a Position."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=position_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        logger.info(f"Position deleted: {position_id}")
        return {"message": "Position deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete Position: {str(e)}")
        return {"error": str(e)}, 400
