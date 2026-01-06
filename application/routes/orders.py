"""
Order Routes for Institutional Trading Platform

Manages all Order-related API endpoints including CRUD operations and workflow transitions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate, validate_querystring

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.order import Order

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["POST"])
@tag(["orders"])
@operation_id("create_order")
@validate(request=Order, responses={201: (Dict[str, Any], None), 400: (Dict[str, Any], None)})
async def create_order(data: Order) -> ResponseReturnValue:
    """Create a new Order"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info("Created Order with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating Order: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Order: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@orders_bp.route("/<entity_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def get_order(entity_id: str) -> ResponseReturnValue:
    """Get Order by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400
        
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        
        if not response:
            return {"error": "Order not found", "code": "NOT_FOUND"}, 404
        
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting Order %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def list_orders() -> ResponseReturnValue:
    """List all Orders"""
    try:
        entities = await service.find_all(
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing Orders: %s", str(e))
        return jsonify({"error": str(e)}), 500


@orders_bp.route("/<entity_id>", methods=["PUT"])
@tag(["orders"])
@operation_id("update_order")
@validate(request=Order, responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def update_order(entity_id: str, data: Order) -> ResponseReturnValue:
    """Update Order"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400
        
        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        transition: Optional[str] = request.args.get("transition")
        
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            transition=transition,
            entity_version=str(Order.ENTITY_VERSION),
        )
        
        logger.info("Updated Order %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating Order %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@orders_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["orders"])
@operation_id("delete_order")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, Any], None)})
async def delete_order(entity_id: str) -> ResponseReturnValue:
    """Delete Order"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400
        
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        
        logger.info("Deleted Order %s", entity_id)
        return {"success": True, "message": "Order deleted successfully", "entity_id": entity_id}, 200
    except Exception as e:
        logger.exception("Error deleting Order %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@orders_bp.route("/<entity_id>/transitions", methods=["GET"])
@tag(["orders"])
@operation_id("get_order_transitions")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def get_order_transitions(entity_id: str) -> ResponseReturnValue:
    """Get available transitions for Order"""
    try:
        transitions = await service.get_transitions(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        return jsonify({"entity_id": entity_id, "available_transitions": transitions}), 200
    except Exception as e:
        logger.exception("Error getting transitions for Order %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500


@orders_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["orders"])
@operation_id("trigger_order_transition")
@validate(responses={200: (Dict[str, Any], None), 500: (Dict[str, Any], None)})
async def trigger_order_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger workflow transition for Order"""
    try:
        transition_name = request.args.get("transition")
        if not transition_name:
            return {"error": "transition parameter required"}, 400
        
        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        
        logger.info("Executed transition '%s' on Order %s", transition_name, entity_id)
        return jsonify({
            "id": response.metadata.id,
            "message": "Transition executed successfully",
            "newState": response.metadata.state,
        }), 200
    except Exception as e:
        logger.exception("Error executing transition on Order %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500

