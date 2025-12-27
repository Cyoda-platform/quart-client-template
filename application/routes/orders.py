import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from application.entity.order import Order
from application.models import OrderRequest, OrderResponse, ErrorResponse
from services.services import get_entity_service

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["POST"])
@tag(["orders"])
@operation_id("create_order")
@validate(
    request=OrderRequest,
    responses={201: (OrderResponse, None), 400: (ErrorResponse, None)},
)
async def create_order(data: OrderRequest) -> ResponseReturnValue:
    """Create new order."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Created order {data.order_id}")
        return _to_dict(response.data), 201
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@orders_bp.route("/<entity_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
@validate(responses={200: (OrderResponse, None), 404: (ErrorResponse, None)})
async def get_order(entity_id: str) -> ResponseReturnValue:
    """Get order by ID."""
    try:
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        if not response:
            return {"error": "Not found"}, 404
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
@validate(responses={200: (Dict[str, Any], None)})
async def list_orders() -> ResponseReturnValue:
    """List all orders."""
    try:
        results = await service.find_all(
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        entities = [_to_dict(r.data) for r in results]
        return {"entities": entities, "total": len(entities)}, 200
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("/<entity_id>", methods=["PUT"])
@tag(["orders"])
@operation_id("update_order")
@validate(
    request=OrderRequest,
    responses={200: (OrderResponse, None), 404: (ErrorResponse, None)},
)
async def update_order(entity_id: str, data: OrderRequest) -> ResponseReturnValue:
    """Update order."""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Updated order {entity_id}")
        return _to_dict(response.data), 200
    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        return {"error": str(e)}, 500


@orders_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["orders"])
@operation_id("delete_order")
@validate(responses={200: (Dict[str, Any], None)})
async def delete_order(entity_id: str) -> ResponseReturnValue:
    """Delete order by ID."""
    try:
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        logger.info(f"Deleted order {entity_id}")
        return {"success": True, "message": "Deleted"}, 200
    except Exception as e:
        logger.error(f"Error deleting order: {str(e)}")
        return {"error": str(e)}, 500


def _to_dict(data: Any) -> Dict[str, Any]:
    """Convert entity to dict."""
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

