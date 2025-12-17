from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service
from application.entity.trade.version_1.trade import Trade

trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")

def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data

@trades_bp.route("", methods=["POST"])
@tag(["trades"])
@operation_id("create_trade")
@validate(request=Trade)
async def create_trade(data: Trade) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@trades_bp.route("/<entity_id>", methods=["GET"])
@tag(["trades"])
@operation_id("get_trade")
async def get_trade(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        if not response:
            return jsonify({"error": "Trade not found"}), 404
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@trades_bp.route("/<entity_id>", methods=["PUT"])
@tag(["trades"])
@operation_id("update_trade")
@validate(request=Trade)
async def update_trade(entity_id: str, data: Trade) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        transition = request.args.get("transition")
        entity_data = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            transition=transition,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@trades_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["trades"])
@operation_id("delete_trade")
async def delete_trade(entity_id: str) -> ResponseReturnValue:
    try:
        service = get_entity_service()
        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        return jsonify({"success": True, "entity_id": entity_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@trades_bp.route("", methods=["GET"])
@tag(["trades"])
@operation_id("list_trades")
async def list_trades() -> ResponseReturnValue:
    try:
        service = get_entity_service()
        args = request.args
        if args:
            builder = SearchConditionRequest.builder()
            for k, v in args.items():
                if k not in ["limit", "offset"]:
                    builder.equals(k, v)
            condition = builder.build()
            results = await service.search(Trade.ENTITY_NAME, condition, str(Trade.ENTITY_VERSION))
        else:
            results = await service.find_all(Trade.ENTITY_NAME, str(Trade.ENTITY_VERSION))
        
        entities = [_to_entity_dict(r.data) for r in results]
        return jsonify({"entities": entities, "total": len(entities)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
