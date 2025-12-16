"""
Order management API routes for the trading platform.

Provides REST endpoints for Order CRUD operations.
"""

import logging
from typing import Any, Dict

from quart import Blueprint
from quart_schema import validate_request, validate_response

from application.entity.order.version_1.order import Order
from services.services import get_entity_service

logger = logging.getLogger(__name__)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["POST"])
@validate_request(Order)
@validate_response(Order, status_code=201)
async def create_order(data: Order) -> tuple[Dict[str, Any], int]:
    """Create a new Order."""
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
        logger.error(f"Failed to create Order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["GET"])
async def get_order(order_id: str) -> tuple[Dict[str, Any], int]:
    """Get Order by technical ID."""
    try:
        entity_service = get_entity_service()
        response = await entity_service.get_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        if response is None:
            return {"error": "Order not found"}, 404
        order_data = response.entity.model_dump(by_alias=True)
        order_data["id"] = response.metadata.id
        order_data["state"] = response.metadata.state
        return order_data, 200
    except Exception as e:
        logger.error(f"Failed to get Order: {str(e)}")
        return {"error": str(e)}, 404


@orders_bp.route("/<order_id>", methods=["PUT"])
@validate_request(Order)
async def update_order(order_id: str, data: Order) -> tuple[Dict[str, Any], int]:
    """Update a Order."""
    try:
        entity_service = get_entity_service()
        order_data = data.model_dump(by_alias=True)
        response = await entity_service.update(
            entity=order_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        order_data["id"] = response.metadata.id
        order_data["state"] = response.metadata.state
        logger.info(f"Order updated: {order_id}")
        return order_data, 200
    except Exception as e:
        logger.error(f"Failed to update Order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["DELETE"])
async def delete_order(order_id: str) -> tuple[Dict[str, str], int]:
    """Delete a Order."""
    try:
        entity_service = get_entity_service()
        await entity_service.delete_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Order deleted: {order_id}")
        return {"message": "Order deleted successfully"}, 200
    except Exception as e:
        logger.error(f"Failed to delete Order: {str(e)}")
        return {"error": str(e)}, 400
