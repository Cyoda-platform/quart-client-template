"""
Order management API routes for the trading platform.

Provides REST endpoints for order CRUD operations and state transitions.
"""

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_response

from application.entity.order.version_1.order import Order
from services.services import get_entity_service

logger = logging.getLogger(__name__)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["POST"])
@validate_request(Order)
@validate_response(Order, status_code=201)
async def create_order(data: Order) -> tuple[Dict[str, Any], int]:
    """
    Create a new order.

    Args:
        data: Order data

    Returns:
        Created order with technical ID
    """
    try:
        entity_service = get_entity_service()

        order_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=order_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        order_data["id"] = response.metadata.id
        order_data["state"] = response.metadata.state

        logger.info(f"Order created: {response.metadata.id}")
        return order_data, 201

    except Exception as e:
        logger.error(f"Failed to create order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["GET"])
async def get_order(order_id: str) -> tuple[Dict[str, Any], int]:
    """
    Get order by technical ID.

    Args:
        order_id: Technical ID of the order

    Returns:
        Order details
    """
    try:
        entity_service = get_entity_service()

        response = await entity_service.get(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        order_data = response.entity.model_dump(by_alias=True)
        order_data["id"] = response.metadata.id
        order_data["state"] = response.metadata.state

        return order_data, 200

    except Exception as e:
        logger.error(f"Failed to get order: {str(e)}")
        return {"error": str(e)}, 404


@orders_bp.route("/<order_id>", methods=["PUT"])
@validate_request(Order)
async def update_order(order_id: str, data: Order) -> tuple[Dict[str, Any], int]:
    """
    Update an order.

    Args:
        order_id: Technical ID of the order
        data: Updated order data

    Returns:
        Updated order
    """
    try:
        entity_service = get_entity_service()

        order_data = data.model_dump(by_alias=True)
        response = await entity_service.save(
            entity=order_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        order_data["id"] = response.metadata.id
        order_data["state"] = response.metadata.state

        logger.info(f"Order updated: {order_id}")
        return order_data, 200

    except Exception as e:
        logger.error(f"Failed to update order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["DELETE"])
async def delete_order(order_id: str) -> tuple[Dict[str, str], int]:
    """
    Delete an order.

    Args:
        order_id: Technical ID of the order

    Returns:
        Deletion confirmation
    """
    try:
        entity_service = get_entity_service()

        await entity_service.delete(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )

        logger.info(f"Order deleted: {order_id}")
        return {"message": "Order deleted successfully"}, 200

    except Exception as e:
        logger.error(f"Failed to delete order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>/transition", methods=["POST"])
async def transition_order(order_id: str) -> tuple[Dict[str, Any], int]:
    """
    Transition order to next state.

    Args:
        order_id: Technical ID of the order

    Returns:
        Updated order with new state
    """
    try:
        entity_service = get_entity_service()
        body = await request.get_json()
        transition_name = body.get("transition")

        if not transition_name:
            return {"error": "Transition name is required"}, 400

        response = await entity_service.transition(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
            transition=transition_name,
        )

        order_data = response.entity.model_dump(by_alias=True)
        order_data["id"] = response.metadata.id
        order_data["state"] = response.metadata.state

        logger.info(f"Order {order_id} transitioned to {response.metadata.state}")
        return order_data, 200

    except Exception as e:
        logger.error(f"Failed to transition order: {str(e)}")
        return {"error": str(e)}, 400

