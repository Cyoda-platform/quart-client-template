"""
Position management routes for institutional trading platform.

Provides REST API endpoints for portfolio position tracking and P&L.
"""

import logging
from typing import Any

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.position.version_1.position import Position
from services.services import get_entity_service

logger = logging.getLogger(__name__)

positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@positions_bp.post("")
@validate_request(Position)
@validate_response(Position, 201)
async def create_position(data: Position) -> tuple[dict[str, Any], int]:
    """Create a new position."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        logger.info(f"Created position: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error creating position: {str(e)}")
        return {"error": str(e)}, 400


@positions_bp.get("/<position_id>")
@validate_response(Position, 200)
async def get_position(position_id: str) -> tuple[dict[str, Any], int]:
    """Get position by ID."""
    try:
        response = await service.get(
            entity_id=position_id,
            entity_class=Position.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting position: {str(e)}")
        return {"error": str(e)}, 404


@positions_bp.put("/<position_id>")
@validate_request(Position)
@validate_response(Position, 200)
async def update_position(
    position_id: str, data: Position
) -> tuple[dict[str, Any], int]:
    """Update a position."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=position_id,
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
        )
        logger.info(f"Updated position: {position_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating position: {str(e)}")
        return {"error": str(e)}, 400


@positions_bp.post("/<position_id>/transitions/<transition_name>")
async def transition_position(
    position_id: str, transition_name: str
) -> tuple[dict[str, Any], int]:
    """Trigger a workflow transition on a position."""
    try:
        response = await service.transition(
            entity_id=position_id,
            transition_name=transition_name,
            entity_class=Position.ENTITY_NAME,
        )
        logger.info(f"Transitioned position {position_id} to {transition_name}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error transitioning position: {str(e)}")
        return {"error": str(e)}, 400

