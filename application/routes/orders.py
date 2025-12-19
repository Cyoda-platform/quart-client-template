import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.order.version_1.order import Order

logger = logging.getLogger(__name__)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@orders_bp.route("", methods=["POST"])
@tag(["orders"])
@operation_id("create_order")
@validate(
    request=Order,
    responses={201: (Dict[str, Any], None), 400: (Dict[str, str], None)},
)
async def create_order(data: Order) -> ResponseReturnValue:
    """Create a new trading order"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Created order {response.metadata.id}")
        return _to_entity_dict(response.data), 201
    except Exception as e:
        logger.exception(f"Error creating order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
@validate(responses={200: (Dict[str, Any], None), 404: (Dict[str, str], None)})
async def get_order(order_id: str) -> ResponseReturnValue:
    """Get order by ID"""
    try:
        response = await get_entity_service().get_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Order not found"}, 404
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error getting order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
@validate(responses={200: (Dict[str, Any], None)})
async def list_orders() -> ResponseReturnValue:
    """List all orders"""
    try:
        entities = await get_entity_service().find_all(
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return {"orders": entity_list, "total": len(entity_list)}, 200
    except Exception as e:
        logger.exception(f"Error listing orders: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["PUT"])
@tag(["orders"])
@operation_id("update_order")
@validate(request=Order, responses={200: (Dict[str, Any], None)})
async def update_order(order_id: str, data: Order) -> ResponseReturnValue:
    """Update an order"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await get_entity_service().update(
            entity_id=order_id,
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Updated order {order_id}")
        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception(f"Error updating order: {str(e)}")
        return {"error": str(e)}, 400


@orders_bp.route("/<order_id>", methods=["DELETE"])
@tag(["orders"])
@operation_id("delete_order")
@validate(responses={200: (Dict[str, str], None)})
async def delete_order(order_id: str) -> ResponseReturnValue:
    """Delete an order"""
    try:
        await get_entity_service().delete_by_id(
            entity_id=order_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Deleted order {order_id}")
        return {"message": "Order deleted successfully"}, 200
    except Exception as e:
        logger.exception(f"Error deleting order: {str(e)}")
        return {"error": str(e)}, 400

