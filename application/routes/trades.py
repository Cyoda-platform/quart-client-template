import logging
from typing import Any, Dict

from quart import Blueprint, jsonify, request
from quart.typing import ResponseReturnValue
from quart_schema import operation_id, tag, validate

from services.services import get_entity_service
from application.entity.trade.version_1.trade import Trade

logger = logging.getLogger(__name__)


class _ServiceProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_entity_service(), name)


service = _ServiceProxy()


def _to_entity_dict(data: Any) -> Dict[str, Any]:
    return data.model_dump(by_alias=True) if hasattr(data, "model_dump") else data


trades_bp = Blueprint("trades", __name__, url_prefix="/api/trades")


@trades_bp.route("", methods=["POST"])
@tag(["trades"])
@operation_id("create_trade")
@validate(
    request=Trade,
    responses={
        201: (Dict[str, Any], None),
        400: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def create_trade(data: Trade) -> ResponseReturnValue:
    """Create a new Trade"""
    try:
        entity_data = data.model_dump(by_alias=True)
        response = await service.save(
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        logger.info("Created Trade with ID: %s", response.metadata.id)
        return _to_entity_dict(response.data), 201
    except ValueError as e:
        logger.warning("Validation error creating Trade: %s", str(e))
        return {"error": str(e), "code": "VALIDATION_ERROR"}, 400
    except Exception as e:
        logger.exception("Error creating Trade: %s", str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@trades_bp.route("/<entity_id>", methods=["GET"])
@tag(["trades"])
@operation_id("get_trade")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def get_trade(entity_id: str) -> ResponseReturnValue:
    """Get Trade by ID"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        response = await service.get_by_id(
            entity_id=entity_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        if not response:
            return {"error": "Trade not found", "code": "NOT_FOUND"}, 404

        return _to_entity_dict(response.data), 200
    except Exception as e:
        logger.exception("Error getting Trade %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@trades_bp.route("", methods=["GET"])
@tag(["trades"])
@operation_id("list_trades")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def list_trades() -> ResponseReturnValue:
    """List all Trades"""
    try:
        entities = await service.find_all(
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )
        entity_list = [_to_entity_dict(r.data) for r in entities]
        return jsonify({"entities": entity_list, "total": len(entity_list)}), 200
    except Exception as e:
        logger.exception("Error listing Trades: %s", str(e))
        return jsonify({"error": str(e)}), 500


@trades_bp.route("/<entity_id>", methods=["PUT"])
@tag(["trades"])
@operation_id("update_trade")
@validate(
    request=Trade,
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    },
)
async def update_trade(entity_id: str, data: Trade) -> ResponseReturnValue:
    """Update Trade"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        entity_data: Dict[str, Any] = data.model_dump(by_alias=True)
        response = await service.update(
            entity_id=entity_id,
            entity=entity_data,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        logger.info("Updated Trade %s", entity_id)
        return jsonify(_to_entity_dict(response.data)), 200
    except Exception as e:
        logger.exception("Error updating Trade %s: %s", entity_id, str(e))
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500


@trades_bp.route("/<entity_id>", methods=["DELETE"])
@tag(["trades"])
@operation_id("delete_trade")
@validate(
    responses={
        200: (Dict[str, Any], None),
        404: (Dict[str, str], None),
        500: (Dict[str, str], None),
    }
)
async def delete_trade(entity_id: str) -> ResponseReturnValue:
    """Delete Trade"""
    try:
        if not entity_id or len(entity_id.strip()) == 0:
            return {"error": "Entity ID is required", "code": "INVALID_ID"}, 400

        await service.delete_by_id(
            entity_id=entity_id,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        logger.info("Deleted Trade %s", entity_id)
        return {"success": True, "message": "Trade deleted successfully"}, 200
    except Exception as e:
        logger.exception("Error deleting Trade %s: %s", entity_id, str(e))
        return {"error": str(e), "code": "INTERNAL_ERROR"}, 500


@trades_bp.route("/<entity_id>/transitions", methods=["POST"])
@tag(["trades"])
@operation_id("trigger_trade_transition")
@validate(
    responses={
        200: (Dict[str, Any], None),
        500: (Dict[str, str], None),
    }
)
async def trigger_trade_transition(entity_id: str) -> ResponseReturnValue:
    """Trigger workflow transition for Trade"""
    try:
        data = await request.get_json()
        transition_name = data.get("transition_name")

        if not transition_name:
            return {"error": "transition_name is required"}, 400

        response = await service.execute_transition(
            entity_id=entity_id,
            transition=transition_name,
            entity_class=Trade.ENTITY_NAME,
            entity_version=str(Trade.ENTITY_VERSION),
        )

        logger.info("Executed transition '%s' on Trade %s", transition_name, entity_id)
        return jsonify({"id": response.metadata.id, "state": response.metadata.state}), 200
    except Exception as e:
        logger.exception("Error executing transition on Trade %s: %s", entity_id, str(e))
        return jsonify({"error": str(e)}), 500

