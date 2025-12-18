"""
Order Routes for Trading Platform

Manages all Order-related API endpoints including CRUD operations
and workflow transitions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.order.version_1.order import Order
from common.exception import is_not_found
from services.services import get_entity_service

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
@validate(
    request=Order, responses={201: (dict, None), 400: (dict, None), 500: (dict, None)}
)
async def create_order(data: Order) -> ResponseReturnValue:
    """Create a new order"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Created order with ID: {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("/<entity_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
@validate(responses={200: (dict, None), 404: (dict, None), 500: (dict, None)})
async def get_order(entity_id: str) -> ResponseReturnValue:
    """Get an order by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Order not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
@validate(responses={200: (dict, None), 500: (dict, None)})
async def list_orders() -> ResponseReturnValue:
    """List all orders"""
    try:
        response = await service.list(
            entity_class=Order.ENTITY_NAME,
            limit=100,
            offset=0,
        )
        orders = [_to_entity_dict(item) for item in response.data]
        return {"orders": orders, "total": len(orders)}, 200
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("/<entity_id>", methods=["PUT"])
@tag(["orders"])
@operation_id("update_order")
@validate(
    request=Order, responses={200: (dict, None), 404: (dict, None), 500: (dict, None)}
)
async def update_order(entity_id: str, data: Order) -> ResponseReturnValue:
    """Update an order"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Order not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("/<entity_id>/transition", methods=["POST"])
@tag(["orders"])
@operation_id("transition_order")
@validate(
    responses={
        200: (dict, None),
        400: (dict, None),
        404: (dict, None),
        500: (dict, None),
    }
)
async def transition_order(entity_id: str) -> ResponseReturnValue:
    """Transition order to next state"""
    try:
        data = await request.get_json()
        transition_name = data.get("transition")

        if not transition_name:
            return {"error": "transition name required"}, 400

        response = await service.transition(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            transition_name=transition_name,
        )
        if is_not_found(response):
            return {"error": "Order not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error transitioning order: {str(e)}")
        return {"error": str(e)}, 500
