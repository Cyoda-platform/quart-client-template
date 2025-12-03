"""
Order Routes for Trading Platform

Manages all Order-related API endpoints including order submission,
execution tracking, and lifecycle management.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from decimal import Decimal

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.order.version_1.order import Order

logger = logging.getLogger(__name__)

# Service proxy
class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)

service = _ServiceProxy()

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

@orders_bp.route("", methods=["POST"])
@tag(["orders"])
@operation_id("submit_order")
async def submit_order() -> ResponseReturnValue:
    """Submit a new trading order"""
    try:
        data = await request.get_json()
        
        # Create Order entity
        order = Order(**data)
        entity_data = order.model_dump(by_alias=True)

        # Save the order
        response = await service.save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        logger.info("Submitted Order with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201

    except ValueError as e:
        logger.warning("Validation error submitting order: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error submitting order: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@orders_bp.route("/<order_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
async def get_order(order_id: str) -> ResponseReturnValue:
    """Get order by ID"""
    try:
        response = await service.get_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Order not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200

    except Exception as e:
        logger.exception("Error getting order %s: %s", order_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500

@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
async def list_orders() -> ResponseReturnValue:
    """List orders with optional filtering"""
    try:
        # Get query parameters
        client_id = request.args.get("clientId")
        symbol = request.args.get("symbol")
        status = request.args.get("status")
        side = request.args.get("side")

        # Build search conditions
        search_conditions = {}
        if client_id:
            search_conditions["clientId"] = client_id
        if symbol:
            search_conditions["symbol"] = symbol
        if status:
            search_conditions["status"] = status
        if side:
            search_conditions["side"] = side

        if search_conditions:
            builder = SearchConditionRequest.builder()
            for field, value in search_conditions.items():
                builder.equals(field, value)
            condition = builder.build()

            entities = await service.search(
                entity_class=Order.ENTITY_NAME,
                condition=condition,
                entity_version=str(Order.ENTITY_VERSION),
            )
        else:
            entities = await service.find_all(
                entity_class=Order.ENTITY_NAME,
                entity_version=str(Order.ENTITY_VERSION),
            )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"orders": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error listing orders: %s", str(e))
        return {"error": str(e)}, 500

@orders_bp.route("/<order_id>/cancel", methods=["POST"])
@tag(["orders"])
@operation_id("cancel_order")
async def cancel_order(order_id: str) -> ResponseReturnValue:
    """Cancel an order"""
    try:
        response = await service.execute_transition(
            entity_id=order_id,
            transition="cancel",
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        logger.info("Cancelled order %s", order_id)
        return {
            "id": response.metadata.id,
            "message": "Order cancelled successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error cancelling order %s: %s", order_id, str(e))
        return {"error": str(e)}, 500

@orders_bp.route("/<order_id>/execute", methods=["POST"])
@tag(["orders"])
@operation_id("execute_order")
async def execute_order(order_id: str) -> ResponseReturnValue:
    """Execute an order"""
    try:
        response = await service.execute_transition(
            entity_id=order_id,
            transition="execute",
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        logger.info("Executed order %s", order_id)
        return {
            "id": response.metadata.id,
            "message": "Order executed successfully",
            "newState": response.metadata.state,
        }, 200

    except Exception as e:
        logger.exception("Error executing order %s: %s", order_id, str(e))
        return {"error": str(e)}, 500

@orders_bp.route("/by-client/<client_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_orders_by_client")
async def get_orders_by_client(client_id: str) -> ResponseReturnValue:
    """Get all orders for a specific client"""
    try:
        builder = SearchConditionRequest.builder()
        builder.equals("clientId", client_id)
        condition = builder.build()

        entities = await service.search(
            entity_class=Order.ENTITY_NAME,
            condition=condition,
            entity_version=str(Order.ENTITY_VERSION),
        )

        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"orders": entity_list, "total": len(entity_list)}, 200

    except Exception as e:
        logger.exception("Error getting orders for client %s: %s", client_id, str(e))
        return {"error": str(e)}, 500
