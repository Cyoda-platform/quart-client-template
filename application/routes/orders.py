"""
Order routes for institutional trading platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.order import Order
from common.exception import is_not_found
from services.services import get_entity_service

logger = logging.getLogger(__name__)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity data to response format."""
    return data if isinstance(data, dict) else data.model_dump(by_alias=True)


@orders_bp.route("", methods=["POST"])
@tag(["orders"])
@operation_id("create_order")
@validate(request=Order)
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
    except Exception as e:
        logger.error("Error creating order: %s", str(e))
        return {"error": str(e)}, 500


@orders_bp.route("/<entity_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
async def get_order(entity_id: str) -> ResponseReturnValue:
    """Get an Order by ID"""
    try:
        response = await service.get(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
        )
        if is_not_found(response):
            return {"error": "Not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.error("Error getting order: %s", str(e))
        return {"error": str(e)}, 500


@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
async def list_orders() -> ResponseReturnValue:
    """List all Orders"""
    try:
        response = await service.list(
            entity_class=Order.ENTITY_NAME,
        )
        return {"data": response.data}, 200
    except Exception as e:
        logger.error("Error listing orders: %s", str(e))
        return {"error": str(e)}, 500
