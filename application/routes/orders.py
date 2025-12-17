from typing import Any, Dict, List, Optional

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.order.version_1.order import Order

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


@orders_bp.route("", methods=["POST"])
@tag(["orders"])
@operation_id("create_order")
@validate(request=Order)
async def create_order(data: Order) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@orders_bp.route("/<entity_id>", methods=["GET"])
@tag(["orders"])
@operation_id("get_order")
async def get_order(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        if not response:
            return jsonify({"error": "Order not found"}), 404
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@orders_bp.route("/<entity_id>", methods=["PUT"])
@tag(["orders"])
@operation_id("update_order")
@validate(request=Order)
async def update_order(entity_id: str, data: Order) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        transition = request.args.get("transition")
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Order.ENTITY_NAME,
            transition=transition,
            entity_version=str(Order.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@orders_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["orders"])
@operation_id("delete_order")
async def delete_order(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Order.ENTITY_NAME,
            entity_version=str(Order.ENTITY_VERSION),
        )
        return jsonify({"success": True, "entity_id": entity_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@orders_bp.route("", methods=["GET"])
@tag(["orders"])
@operation_id("list_orders")
async def list_orders() -> ResponseReturnValue:
    try:
        service = get_entity_service()
        # Basic search via query params
        args = request.args
        if args:
            builder = SearchConditionRequest.builder()
            for k, v in args.items():
                if k not in ["limit", "offset"]:
                    builder.equals(k, v)
            condition = builder.build()
            results = await service.search(
                Order.ENTITY_NAME, condition, str(Order.ENTITY_VERSION)
            )
        else:
            results = await service.find_all(
                Order.ENTITY_NAME, str(Order.ENTITY_VERSION)
            )

        entities = [_to_entity_dict(r.data) for r in results]
        return jsonify({"entities": entities, "total": len(entities)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
