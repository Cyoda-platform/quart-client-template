"""
Order Routes for Real-Time Trading Platform

Manages all Order-related API endpoints including CRUD operations
and workflow transitions for trading order management.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue

from common.exception import is_not_found
from common.service.entity_service import SearchCondition, SearchConditionRequest, SearchOperator
from services.services import get_entity_service
from application.entity.order.version_1.order import Order

# Create blueprint for order routes
orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

logger = logging.getLogger(__name__)


@orders_bp.route("", methods=["POST"])
async def create_order() -> ResponseReturnValue:
    """Create a new order"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        entity_service = get_entity_service()
        
        # Save the order
        response = await entity_service.save(
            entity=data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        return jsonify({
            "id": response.metadata.id,
            "state": response.metadata.state,
            "message": "Order created successfully"
        }), 201

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return jsonify({"error": "Failed to create order"}), 500


@orders_bp.route("/<order_id>", methods=["GET"])
async def get_order(order_id: str) -> ResponseReturnValue:
    """Get order by ID"""
    try:
        entity_service = get_entity_service()
        
        response = await entity_service.get_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        if response is None:
            return jsonify({"error": "Order not found"}), 404

        return jsonify(response.entity), 200

    except Exception as e:
        logger.error(f"Error getting order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to get order"}), 500


@orders_bp.route("", methods=["GET"])
async def list_orders() -> ResponseReturnValue:
    """List all orders with optional filtering"""
    try:
        entity_service = get_entity_service()
        
        # Get query parameters
        portfolio_id = request.args.get("portfolio_id")
        symbol = request.args.get("symbol")
        status = request.args.get("status")
        
        # Build search conditions if filters provided
        conditions = []
        if portfolio_id:
            conditions.append(SearchCondition(
                field="portfolioId",
                operator=SearchOperator.EQUALS,
                value=portfolio_id
            ))
        if symbol:
            conditions.append(SearchCondition(
                field="symbol",
                operator=SearchOperator.EQUALS,
                value=symbol.upper()
            ))
        if status:
            conditions.append(SearchCondition(
                field="state",
                operator=SearchOperator.EQUALS,
                value=status
            ))

        if conditions:
            search_request = SearchConditionRequest(conditions=conditions)
            response = await entity_service.search(
                entity_class=Order.ENTITY_NAME,
                condition=search_request,
                entity_version=str(Order.ENTITY_VERSION),
            )
            orders = [r.entity for r in response]
        else:
            response = await entity_service.find_all(
                entity_class=Order.ENTITY_NAME,
                entity_version=str(Order.ENTITY_VERSION),
            )
            orders = [r.entity for r in response]

        return jsonify({
            "orders": orders,
            "count": len(orders)
        }), 200

    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        return jsonify({"error": "Failed to list orders"}), 500


@orders_bp.route("/<order_id>", methods=["PUT"])
async def update_order(order_id: str) -> ResponseReturnValue:
    """Update an existing order"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        entity_service = get_entity_service()
        
        # Get transition if specified
        transition = data.pop("transition", None)
        
        response = await entity_service.update(
            entity_id=order_id,
            entity=data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
            transition=transition,
        )

        if response is None:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({
            "id": response.metadata.id,
            "state": response.metadata.state,
            "message": "Order updated successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error updating order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to update order"}), 500


@orders_bp.route("/<order_id>/cancel", methods=["POST"])
async def cancel_order(order_id: str) -> ResponseReturnValue:
    """Cancel an order"""
    try:
        entity_service = get_entity_service()
        
        response = await entity_service.update(
            entity_id=order_id,
            entity={},
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
            transition="cancel",
        )

        if response is None:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({
            "id": response.metadata.id,
            "state": response.metadata.state,
            "message": "Order cancelled successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to cancel order"}), 500


@orders_bp.route("/<order_id>/fill", methods=["POST"])
async def fill_order(order_id: str) -> ResponseReturnValue:
    """Fill an order (trigger execution)"""
    try:
        entity_service = get_entity_service()
        
        response = await entity_service.update(
            entity_id=order_id,
            entity={},
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
            transition="fill",
        )

        if response is None:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({
            "id": response.metadata.id,
            "state": response.metadata.state,
            "message": "Order fill triggered successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error filling order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to fill order"}), 500


@orders_bp.route("/<order_id>", methods=["DELETE"])
async def delete_order(order_id: str) -> ResponseReturnValue:
    """Delete an order"""
    try:
        entity_service = get_entity_service()
        
        deleted_id = await entity_service.delete_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        return jsonify({"message": "Order deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to delete order"}), 500
