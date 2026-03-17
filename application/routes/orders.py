"""
Order management routes for institutional trading platform.

Provides REST API endpoints for order lifecycle management.
"""

import logging
from typing import Any

from quart import Blueprint, request
from quart_schema import validate_request, validate_response

from application.entity.order.version_1.order import Order
from services.services import get_entity_service

logger = logging.getLogger(__name__)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


class _ServiceProxy:
    """Lazy proxy to avoid initializing services at import time."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


@orders_bp.post("")
@validate_request(Order)
@validate_response(Order, 201)
async def create_order(data: Order) -> tuple[dict[str, Any], int]:
    """Create a new order."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Created order: {response.metadata.id}")
        return response.data, 201
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.get("/<order_id>")
@validate_response(Order, 200)
async def get_order(order_id: str) -> tuple[dict[str, Any], int]:
    """Get order by ID."""
    try:
        response = await service.get(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
        )
        return response.data, 200
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        return {"error": str(e)}, 404


@orders_bp.put("/<order_id>")
@validate_request(Order)
@validate_response(Order, 200)
async def update_order(order_id: str, data: Order) -> tuple[dict[str, Any], int]:
    """Update an order."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=order_id,
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
        )
        logger.info(f"Updated order: {order_id}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.post("/<order_id>/transitions/<transition_name>")
async def transition_order(
    order_id: str, transition_name: str
) -> tuple[dict[str, Any], int]:
    """Trigger a workflow transition on an order."""
    try:
        response = await service.transition(
            entity_id=order_id,
            transition_name=transition_name,
            entity_class=Order.ENTITY_NAME,
        )
        logger.info(f"Transitioned order {order_id} to {transition_name}")
        return response.data, 200
    except Exception as e:
        logger.error(f"Error transitioning order: {str(e)}")
        return {"error": str(e)}, 400
