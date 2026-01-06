"""
Position Routes for Institutional Trading Platform

Manages all Position-related API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.position import Position

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


positions_bp = Blueprint("positions", __name__, url_prefix="/api/positions")


@positions_bp.route("", methods=["POST"])
@tag(["positions"])
@operation_id("create_position")
@validate(request=Position, responses={201: (Dict[str, Any], None), 400: (Dict[str, Any], None)})
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
    except ValueError as e:
        logger.warning("Validation error creating Position: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Position: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@positions_bp.route("/<entity_id>", methods=["GET"])
@tag(["positions"])
@operation_id("get_position")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def get_position(entity_id: str) -> ResponseReturnValue:
    """Get Position by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400
        
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        
        if not response:
            return {"error": "Position not found", "code": "NOT_FOUND"}, 404
        
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting Position %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@positions_bp.route("", methods=["GET"])
@tag(["positions"])
@operation_id("list_positions")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def list_positions() -> ResponseReturnValue:
    """List all Positions"""
    try:
        entities = await service.find_all(
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing Positions: %s", str(e))
        return jsonify({"error": str(e)}), 500


@positions_bp.route("/<entity_id>", methods=["PUT"])
@tag(["positions"])
@operation_id("update_position")
@validate(request=Position, responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def update_position(entity_id: str, data: Position) -> ResponseReturnValue:
    """Update Position"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400
        
        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        transition: Optional[str] = request.args.get("transition")
        
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Position.ENTITY_NAME,
            transition=transition,
            entity_version=str(Position.ENTITY_VERSION),
        )
        
        logger.info("Updated Position %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating Position %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@positions_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["positions"])
@operation_id("delete_position")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def delete_position(entity_id: str) -> ResponseReturnValue:
    """Delete Position"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400
        
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        
        logger.info("Deleted Position %s", entity_id)
        return {"success": True, "message": "Position deleted successfully", "entity_id": entity_id}, 200
    except Exception as e:
        logger.exception("Error deleting Position %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@positions_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["positions"])
@operation_id("get_position_transitions")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def get_position_transitions(entity_id: str) -> ResponseReturnValue:
    """Get available transitions for Position"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        return jsonify({"entity_id": entity_id, "available_transitions": transitions}), 200
    except Exception as e:
        logger.exception("Error getting transitions for Position %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500


@positions_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["positions"])
@operation_id("trigger_position_transition")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def trigger_position_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger workflow transition for Position"""
    try:
        transition_name = request.args.get("transition")
        if not transition_name:
            return {"error": "transition parameter required"}, 400
        
        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Position.ENTITY_NAME,
            entity_version=str(Position.ENTITY_VERSION),
        )
        
        logger.info("Executed transition '%s' on Position %s", transition_name, entity_id)
        return jsonify({
            "id": response.metadata.id,
            "message": "Transition executed successfully",
            "newState": response.metadata.state,
        }), 200
    except Exception as e:
        logger.exception("Error executing transition on Position %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500

